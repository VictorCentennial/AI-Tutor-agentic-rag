# Import LangChain components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

# from langchain.document_loaders import TextLoader
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableSequence
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ChatMessage

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.memory import MemorySaver

from langgraph.graph import START, END, StateGraph


from typing import TypedDict, Annotated
from datetime import timedelta, datetime


class AgentState(TypedDict):
    subject: str
    topic: str
    context: str
    summary: str
    messages: Annotated[list, add_messages]
    answer_trials: int
    start_time: datetime
    duration_minutes: int


class AiTutorAgent:
    def __init__(
        self, GOOGLE_MODEL_NAME: str, GOOGLE_API_KEY: str, memory: MemorySaver
    ):
        self.llm = ChatGoogleGenerativeAI(
            model=GOOGLE_MODEL_NAME, google_api_key=GOOGLE_API_KEY
        )
        self.memory = memory

        builder = StateGraph(AgentState)
        builder.add_node("create_summary", self.create_summary)
        builder.add_node("greeting", self.greeting)
        builder.add_node("student_input", self.student_input)
        builder.add_node("reask_question", self.reask_question)
        builder.add_node("llm_answer_question", self.llm_answer_question)
        builder.add_node("student_answer_question", self.student_answer_question)
        builder.add_node("add_wrong_answer_trials", self.add_wrong_answer_trials)
        builder.add_node(
            "tell_student_answer_is_correct", self.tell_student_answer_is_correct
        )
        builder.add_node("hints", self.hints)
        builder.add_node("explain_answer", self.explain_answer)
        builder.add_node("intermediate_summary", self.intermediate_summary)
        builder.add_node(
            "student_answer_if_any_further_question",
            self.student_answer_if_any_further_question,
        )
        builder.add_node("session_summary", self.session_summary)
        builder.add_node("ask_new_question", self.ask_new_question)
        builder.add_node("time_out_message", self.time_out_message)
        builder.add_edge(START, "create_summary")
        builder.add_edge("create_summary", "greeting")
        builder.add_edge("greeting", "student_input")
        builder.add_edge("reask_question", "student_input")
        builder.add_conditional_edges(
            "student_input",
            self.question_guarding,
            {
                "TimeOut": "time_out_message",
                "Pass": "llm_answer_question",
                "Fail": "reask_question",
            },
        )
        builder.add_edge("llm_answer_question", "student_answer_question")
        builder.add_conditional_edges(
            "student_answer_question",
            self.further_question_correctness,
            {
                "TimeOut": "time_out_message",
                "Correct": "tell_student_answer_is_correct",
                "Wrong": "add_wrong_answer_trials",
                "Stop": "explain_answer",
            },
        )
        builder.add_edge("tell_student_answer_is_correct", "intermediate_summary")
        builder.add_edge("add_wrong_answer_trials", "hints")
        builder.add_edge("hints", "student_answer_question")
        builder.add_edge("explain_answer", "intermediate_summary")
        builder.add_edge(
            "intermediate_summary", "student_answer_if_any_further_question"
        )
        builder.add_conditional_edges(
            "student_answer_if_any_further_question",
            self.any_further_question,
            {
                "TimeOut": "time_out_message",
                "Yes": "ask_new_question",
                "No": "session_summary",
            },
        )
        builder.add_edge("time_out_message", "session_summary")
        builder.add_edge("ask_new_question", "student_input")
        builder.add_edge("session_summary", END)

        self.graph = builder.compile(
            checkpointer=memory,
            interrupt_before=[
                "student_input",
                "student_answer_question",
                "student_answer_if_any_further_question",
            ],
        )

        self.SUMMARY_PROMPT = """
        Create a summary of the topics included in the context.
        context: {context}
        """

        self.GREETING_PROMPT = """
        You are an AI Tutor. You are given a topic and a subject.
        You need to create a greeting message for the student,
        asking them what they want to learn based on the subject, topic and content summary.
        Keep the greeting short and concise.

        Subject: {subject}
        Topic: {topic}
        Content summary of the topic: {summary}
        """

        self.QUESTION_GUARDING_PROMPT = """
        You are an AI Tutor. Based on the content summary of the topic, 
        you need to decide if the student's question is related to the content summary.
        For educational purpose, it is ok to be related but not exactly the same topic.
        If it is, respond "Pass".  
        If it is not, respond "Fail" 

        Student Question: {question}
        Content summary of the topic: {summary}
        """

        self.QUESTION_ANSWERING_PROMPT = """
        You are an AI Tutor. You are given a question and a topic.
        You need to answer the question based on the context.
        After finishing explaining, ask the student a question to check their understanding.

        Question: {question}
        Context: {context}
        """

        self.CHECK_QUESTION_ANSWER_PROMPT = """
            You are an AI Tutor evaluating a student's answer. 
            Compare their response to the context, consider **ONLY the latest answer**,
            determine if it answering the question correctly, demonstrates understanding of the concept.
            If it is, respond "Correct". If it is not, respond "Wrong".

        Question and Answer:
        {question_answer_context}

        Reference Context: 
        {context}
        """

        self.HINTS_PROMPT = """
            You are an AI Tutor. Based on the question and student's answer, 
            understand the student's misconcept and provide hints to the student to help them answer the question.

            Question Answer context: {question_answer_context}
            """

        self.INTERMEDIATE_SUMMARY_PROMPT = """
            You are an AI Tutor. Based on all the previous conversations with student, create a summary of the session.
            Focus on the key concepts and ideas that the student has learnt.
            At the end of the summary, ask the student if there any other questions.

            Question Answer context: {question_answer_context}
            """

        self.ANY_FURTHER_QUESTION_PROMPT = """
            Based on the student's answer, determine if the student has any further questions.
            If the student has any further questions, respond "Yes". If not, respond "No".

            Student Answer: {student_answer}
            """

        self.EXPLAIN_ANSWER_PROMPT = """
            You are an AI Tutor. 
            First, thanks for the effort of answering the question.
            Based on the question and student's answer, 
            explain the correct answer to the student. 
            Keep the explanation short and concise. 
            Forcus on the key concepts and ideas based on student's wrong answer.

            Question Answer context: {question_answer_context}
            """

        self.SESSION_SUMMARY_PROMPT = """
            You are an AI Tutor. Based on all the previous conversations with student, create a concise summary of the session.
            Focus on the key concepts and ideas that the student has learnt.

            Messages: {messages}
            """

    def create_summary(self, state: AgentState):
        response = self.llm.invoke(self.SUMMARY_PROMPT.format(context=state["context"]))
        return {"summary": response.content}

    def greeting(self, state: AgentState):
        subject = state["subject"]
        topic = state["topic"]
        messages = state["messages"]
        summary = state["summary"]

        greeting_prompt = self.GREETING_PROMPT.format(
            subject=subject, topic=topic, summary=summary
        )
        messages = [
            HumanMessage(content=greeting_prompt.format(subject=subject, topic=topic))
        ]
        response = self.llm.invoke(messages)
        return {"messages": response}

    def student_input(self, state: AgentState):
        # print(state["messages"][-1].content)
        return state

    # helper function
    def time_out(self, state: AgentState):
        current_time = datetime.now()
        start_time = state["start_time"]
        duration_minutes = state["duration_minutes"]
        return (current_time - start_time) > timedelta(minutes=duration_minutes)

    def question_guarding(self, state: AgentState):
        if self.time_out(state):
            return "TimeOut"
        question = state["messages"][-1].content
        summary = state["summary"]
        response = self.llm.invoke(
            self.QUESTION_GUARDING_PROMPT.format(question=question, summary=summary)
        )
        content = response.content
        if content.startswith("Pass"):
            return "Pass"
        else:
            return "Fail"

    def reask_question(self, state: AgentState):
        return {
            "messages": [
                AIMessage(
                    content="Your question is not related to the topic. Please ask a question related to the topic."
                )
            ]
        }

    def llm_answer_question(self, state: AgentState):
        # print("Answer the question: ", state["messages"][-1].content)
        question = state["messages"][-1].content
        response = self.llm.invoke(
            self.QUESTION_ANSWERING_PROMPT.format(
                question=question, context=state["context"]
            )
        )
        result = response.content
        return {"messages": [AIMessage(content=result)]}

    def student_answer_question(self, state: AgentState):
        # print(state["messages"][-1].content)
        return state

    # helper function
    # TODO: use trim_message library
    def get_question_answer_context(self, state: AgentState):
        answer_trials = state["answer_trials"]
        number_of_related_messages = (answer_trials + 1) * 2
        question_answer_context = state["messages"][-number_of_related_messages:]
        # print(f"number_of_related_messages: {number_of_related_messages}")
        # print(f"question_answer_context for get_question_answer_context: {question_answer_context}")
        return question_answer_context

    # TODO: need further verify if anwser_trials is correct
    def further_question_correctness(self, state: AgentState, max_trials=3):
        if self.time_out(state):
            return "TimeOut"

        answer_trials = state["answer_trials"]
        if answer_trials >= max_trials:
            return "Stop"

        question_answer_context = self.get_question_answer_context(state)
        context = state["context"]

        response = self.llm.invoke(
            self.CHECK_QUESTION_ANSWER_PROMPT.format(
                question_answer_context=question_answer_context, context=context
            )
        )

        result = response.content.strip()
        return "Correct" if result.startswith("Correct") else "Wrong"
        # need to add one trials for answer_trials

    def tell_student_answer_is_correct(self, state: AgentState):
        return {"messages": [AIMessage(content="Your answer is correct.")]}

    def add_wrong_answer_trials(self, state: AgentState):
        return {"answer_trials": state["answer_trials"] + 1}

    def hints(self, state: AgentState):
        question_answer_context = self.get_question_answer_context(state)
        print(f"question_answer_context for hints: {question_answer_context}")
        response = self.llm.invoke(
            self.HINTS_PROMPT.format(question_answer_context=question_answer_context)
        )
        result = response.content
        return {"messages": [AIMessage(content=result)]}

    def explain_answer(self, state: AgentState):
        question_answer_context = self.get_question_answer_context(state)
        response = self.llm.invoke(
            self.EXPLAIN_ANSWER_PROMPT.format(
                question_answer_context=question_answer_context
            )
        )
        result = response.content
        return {"messages": [AIMessage(content=result)]}

    def intermediate_summary(self, state: AgentState):
        question_answer_context = self.get_question_answer_context(state)
        response = self.llm.invoke(
            self.INTERMEDIATE_SUMMARY_PROMPT.format(
                question_answer_context=question_answer_context
            )
        )
        result = response.content
        return {"messages": [AIMessage(content=result)]}

    def student_answer_if_any_further_question(self, state: AgentState):
        return state

    def any_further_question(self, state: AgentState):
        if self.time_out(state):
            return "TimeOut"
        student_answer = state["messages"][-1].content
        response = self.llm.invoke(
            self.ANY_FURTHER_QUESTION_PROMPT.format(student_answer=student_answer)
        )
        result = response.content
        if result.startswith("Yes"):
            return "Yes"
        else:
            return "No"

    def time_out_message(self, state: AgentState):
        return {
            "messages": [
                AIMessage(content="Time is up. We will summarize the session now.")
            ]
        }

    def session_summary(self, state: AgentState):
        messages = state["messages"]
        response = self.llm.invoke(
            self.SESSION_SUMMARY_PROMPT.format(messages=messages)
        )
        result = response.content
        return {"messages": [AIMessage(content=result)]}

    def ask_new_question(self, state: AgentState):
        return {"messages": [AIMessage(content="What is your next question?")]}
