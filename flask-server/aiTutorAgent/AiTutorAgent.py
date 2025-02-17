# Import LangChain components
import os
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


from typing import TypedDict, Annotated, List
from datetime import timedelta, datetime
from langchain.schema import Document
from langchain.vectorstores.base import VectorStore
from rag import rag


class AgentState(TypedDict):
    subject: str
    topic: str
    titles: List[str]
    summary: str
    messages: Annotated[list, add_messages]
    answer_trials: int
    start_time: datetime
    duration_minutes: int
    tutor_question: str


class AiTutorAgent:
    def __init__(
        self, GOOGLE_MODEL_NAME: str, GOOGLE_API_KEY: str, memory: MemorySaver
    ):
        self.llm = ChatGoogleGenerativeAI(
            model=GOOGLE_MODEL_NAME, google_api_key=GOOGLE_API_KEY
        )
        self.memory = memory
        self.vector_store = None  # Store as instance variable as it cannot store a state, not serializable

        @property
        def vector_store(self):
            """Get the vector store"""
            if self._vector_store is None:
                raise ValueError("Vector store not initialized")
            return self._vector_store

        @vector_store.setter
        def vector_store(self, value):
            """Set the vector store"""
            if not isinstance(value, VectorStore):
                raise TypeError(f"Expected VectorStore, got {type(value)}")
            self._vector_store = value

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
        builder.add_node("ask_any_further_question", self.ask_any_further_question)
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
        builder.add_edge("intermediate_summary", "ask_any_further_question")
        builder.add_edge(
            "ask_any_further_question", "student_answer_if_any_further_question"
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
            Generate a concise summary of the key topics present in the provided titles. 
            List a few key topics in bullet points.

            titles: {titles}
        """

        self.GREETING_PROMPT = """
            You are an AI Tutor. You are given a subject and a topic with its content summary.

            **Instructions**:

            - Warmly greet the student as their dedicated AI Tutor and express your commitment to assisting them.
            - Briefly explain what they can learn in this tutoring session based on the content summary of the topic.
            - Provide possible key concepts and ideas they will explore.
            - At the end, ask them to share any specific questions or areas they're interested in.
            - Keep the greeting short and concise.
            - Use simple and easy-to-understand language.

            ---

            **Subject**: {subject}

            **Content Summary of the Topic**: {summary}
        """

        self.QUESTION_GUARDING_PROMPT = """
            You are an AI Tutor.

            **Instructions**:

            1. **Evaluate the Student's Question**:
            - Determine whether the student's question is related to the topic as described in the content summary.
            - It is acceptable if the question is not explicitly mentioned in the content summary, as long as it pertains to the overall subject.

            2. **Response Guidelines**:
            - If the student's question is related to the topic, respond with **"Pass"**.
            - If the student's question is not related to the topic, respond with **"Fail"**.

            3. **Note**:
            - Provide only the one-word response ("Pass" or "Fail") without any additional comments.

            ---

            **Student Question**:
            {question}

            **Content Summary of the Topic**:
            {summary}
        """
        ##TODO: extract the equation out to consider directly
        self.QUESTION_ANSWERING_PROMPT = """
        
            You are an AI Tutor tasked with assisting a student based on a given question and the result from document search.

            Instructions:
            1. **Answer the Question**: Provide a detailed answer to the question using the result from document search. Incorporate examples to enhance understanding.
                If possible, provide coding examples or diagrams to help the student understand the concept.

            2. **Use Own Knowledge if Necessary**: If the document search does not provide the information needed, 
                ignore the document result and draw upon your own knowledge to answer comprehensively.

            3. **Create a Testing Question**: After your explanation, formulate an exam-style question that effectively assesses the student's understanding of the topic.
            
            4. Question is at the end of the conversation.
            
            5. **Output Formatting**:
            - Present your **answer to student's question** and the **testing question** to the student in clear, student-friendly language.
            - Do **not** include  answer to the testing question in your response to the student.

                ---

            **Student's Question**: {question}

            **Result from document search**: {result_from_document_search}
        """

        self.CHECK_QUESTION_ANSWER_PROMPT = """
            You are an AI Tutor evaluating a student's answer.

            **Instructions**:

            - Consider the AI question and student's answer, evaluate e if it correctly answers the initial question and demonstrates understanding of the concept.
            - **Response**:
            - If the student's answer is correct and shows understanding, respond with **"Correct"**.
            - If the student's answer is incorrect or shows misunderstanding, respond with **"Wrong"**.
            - Provide a one-word response ("Correct" or "Wrong") without any additional hints or feedback.

            ---

            **AI Question**:

            {question}
            
            **Student's Answer**:

            {answer}
        """

        self.HINTS_PROMPT = """
                You are an AI Tutor. Based on the question and the student's latest answer, provide constructive feedback to help the student understand and correct their mistakes.

                **Instructions**:

                1. **Explain Why the Answer is Wrong**:
                - Clearly and respectfully explain why the student's answer is incorrect.
                - Point out any errors or inaccuracies in their response without being discouraging.

                2. **Identify Misconceptions**:
                - Analyze the student's answer to identify any underlying misconceptions or misunderstandings.
                - Briefly explain these misconceptions to help the student recognize and correct them.

                3. **Provide Hints and Guidance**:
                - Offer tips, clues, or a step-by-step guideline that will assist the student in finding the correct answer on their own.
                - Use guiding questions or prompts to encourage critical thinking.
                - **Do not** reveal the correct answer directly.

                **Note**: Maintain an encouraging and supportive tone to foster a positive learning environment.

                ---

                **Question and Answer Context**:

                {question_answer_context}

            """

        self.INTERMEDIATE_SUMMARY_PROMPT = """
            You are an AI Tutor.

            **Intermediate Summary Instructions**:

            1. **Review the Conversation**:
            - Reflect on all the previous interactions with the student during the question answering session.
            - Identify the key concepts, ideas, and skills that were discussed.

            2. **Create a Summary**:
            - Write a concise and clear summary of the session.
            - Focus on the main topics covered and the key concepts the student has learned or improved upon.
            - Highlight any progress the student made, including overcoming misconceptions or mastering difficult concepts.

            **Question and Answer Context**:

            {question_answer_context}
        """

        self.ANY_FURTHER_QUESTION_PROMPT = """
            Any further questions related to this course?
            """

        self.EXPLAIN_ANSWER_PROMPT = """
                You are an AI Tutor.

                **Instructions**:

                1. **Express Appreciation and Encouragement**:
                - Begin by thanking the student for their efforts and persistence in attempting to answer the question multiple times.
                - Offer words of encouragement to acknowledge their dedication and to motivate them.

                2. **Provide the Correct Answer**:
                - Clearly and concisely explain the correct answer to the question.
                - Focus on the key concepts and ideas essential to understanding the answer.
                - Keep the explanation straightforward and accessible.

                3. **Address Misconceptions**:
                - Gently point out any misunderstandings or errors in the student's previous answers.
                - Clarify these misconceptions to help the student grasp the correct concepts.

                **Note**: Maintain a supportive and positive tone throughout the explanation to foster a positive learning environment.

                ---

                **Question and Answer Context**:
                {question_answer_context}

            """

        self.SESSION_SUMMARY_PROMPT = """
                You are an AI Tutor.

                **Overall Summary Instructions**: 

                1. **Review All Previous Interactions**:
                - Reflect on all conversations you've had with the student, including the current session and any prior sessions.
                - Identify the main topics, key concepts, and skills that were covered throughout these interactions.
                - **Do not** include the any topics which have not go through with the student.

                2. **Create a Concise Summary**:
                - Write a clear and concise summary of the entire tutoring experience.
                - Focus on the progression of the student's learning, highlighting how their understanding has developed over time.
                - Emphasize the key concepts and ideas the student has learned, as well as any significant improvements or achievements.

                3. **Highlight Learning Milestones**:
                - Mention any challenges the student overcame.
                - Note any recurring themes or concepts that were reinforced across sessions.

                4. **Maintain a Positive Tone**:
                - Use encouraging language to acknowledge the student's efforts and accomplishments.
                - Avoid any negative or discouraging remarks.

                **Note**: Keep the summary student-centered and supportive to foster a positive learning experience.

                ---

                **Messages**:

                {messages}
            """
        

    def general_analysis(self):
        # Analyze all sessions
        session_files = self._get_all_session_files()
        combined_content = self._combine_session_files(session_files)
        return self._generate_analysis("General Analysis", combined_content)

    def student_analysis(self, student_id: str):
        # Analyze sessions for a specific student
        session_files = self._get_session_files_by_student(student_id)
        combined_content = self._combine_session_files(session_files)
        return self._generate_analysis(f"Student {student_id} Analysis", combined_content)

    def course_analysis(self, course_code: str):
        # Analyze sessions for a specific course
        session_files = self._get_session_files_by_course(course_code)
        combined_content = self._combine_session_files(session_files)
        return self._generate_analysis(f"Course {course_code} Analysis", combined_content)

    def day_analysis(self, date: str):
        # Analyze sessions for a specific day
        session_files = self._get_session_files_by_date(date)
        combined_content = self._combine_session_files(session_files)
        return self._generate_analysis(f"Day {date} Analysis", combined_content)

    def _get_all_session_files(self):
        SESSION_HISTORY_DIR = "saved_session_history"
        return [os.path.join(SESSION_HISTORY_DIR, f) for f in os.listdir(SESSION_HISTORY_DIR) if f.endswith(".txt")]

    def _get_session_files_by_student(self, student_id: str):
        SESSION_HISTORY_DIR = "saved_session_history"
        return [os.path.join(SESSION_HISTORY_DIR, f) for f in os.listdir(SESSION_HISTORY_DIR) if f.endswith(f"_{student_id}.txt")]

    def _get_session_files_by_course(self, course_code: str):
        SESSION_HISTORY_DIR = "saved_session_history"
        return [os.path.join(SESSION_HISTORY_DIR, f) for f in os.listdir(SESSION_HISTORY_DIR) if f.split("_")[1] == course_code]

    def _get_session_files_by_date(self, date: str):
        SESSION_HISTORY_DIR = "saved_session_history"
        return [os.path.join(SESSION_HISTORY_DIR, f) for f in os.listdir(SESSION_HISTORY_DIR) if f.startswith(date)]

    def _combine_session_files(self, session_files: list):
        combined_content = ""
        for filepath in session_files:
            with open(filepath, "r") as file:
                combined_content += file.read() + "\n"
        return combined_content

    def _generate_analysis(self, title: str, content: str):
        # Use LLM to generate analysis
        prompt = f"""
            Analyze the following session data for {title}:
            {content}

            Provide a summary of:
            1. Key topics covered.
            2. Types of questions asked.
            3. Concepts learned.
            4. Difficulties faced.
        """
        response = self.llm.invoke(prompt)
        return {"summary": response.content}

    def create_summary(self, state: AgentState):
        response = self.llm.invoke(self.SUMMARY_PROMPT.format(titles=state["titles"]))
        return {"summary": response.content}

    def greeting(self, state: AgentState):
        subject = state["subject"]
        # topic = state["topic"]
        summary = state["summary"]
        greeting_prompt = self.GREETING_PROMPT.format(subject=subject, summary=summary)
        messages = [HumanMessage(content=greeting_prompt)]
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
        while True:
            question = state["messages"][-1].content
            # Use instance vector_store instead of state
            if self.vector_store is None:
                raise ValueError(
                    "Vector store not initialized. Call set_vector_store first."
                )

            vector_search_results = self.vector_store.similarity_search(question, k=3)
            print(f"vector_search_results: {vector_search_results}")
            result_from_document_search = (
                "\n\n".join([doc.page_content for doc in vector_search_results])
                if vector_search_results
                else ""
            )
            response = self.llm.invoke(
                self.QUESTION_ANSWERING_PROMPT.format(
                    question=question,
                    result_from_document_search=result_from_document_search,
                )
            )
            result = response.content
            result_parts = result.split("Question")
            if len(result_parts) > 1:
                tutor_question = result_parts[-1].strip()
            else:
                tutor_question = (
                    None  # or handle the case where "Question" is not found
                )
            if tutor_question:
                break
        return {
            "messages": [AIMessage(content=result)],
            "answer_trials": 0,
            "tutor_question": tutor_question,
        }

    def student_answer_question(self, state: AgentState):
        # print(state["messages"][-1].content)
        return state

    # helper function
    # TODO: use trim_message library
    def get_question_answer_context(self, state: AgentState):
        answer_trials = state["answer_trials"]
        number_of_related_messages = (answer_trials + 1) * 2
        messages = state["messages"][(-1 * number_of_related_messages) :]

        # Convert messages into conversation format
        conversation = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                conversation.append(f"AI: {msg.content}")
            elif isinstance(msg, HumanMessage):
                conversation.append(f"Student: {msg.content}")

        return "\n".join(conversation)

    def further_question_correctness(self, state: AgentState, max_trials=3):
        if self.time_out(state):
            return "TimeOut"

        answer_trials = state["answer_trials"]
        if answer_trials >= max_trials:
            return "Stop"

        answer = state["messages"][-1].content
        question = state["tutor_question"]

        response = self.llm.invoke(
            self.CHECK_QUESTION_ANSWER_PROMPT.format(question=question, answer=answer)
        )

        result = response.content.strip()
        return "Correct" if result.lower().startswith("correct") else "Wrong"
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

    def ask_any_further_question(self, state: AgentState):
        return {"messages": [AIMessage(content=self.ANY_FURTHER_QUESTION_PROMPT)]}

    def student_answer_if_any_further_question(self, state: AgentState):
        return state

    def any_further_question(self, state: AgentState):
        if self.time_out(state):
            return "TimeOut"
        student_answer = state["messages"][-1].content
        return student_answer
        # response = self.llm.invoke(
        #     self.ANY_FURTHER_QUESTION_PROMPT.format(student_answer=student_answer)
        # )
        # result = response.content
        # if result.startswith("Yes"):
        #     return "Yes"
        # else:
        #     return "No"

    def time_out_message(self, state: AgentState):
        return state
        # return {
        #     "messages": [
        #         AIMessage(content="Time is up. We will summarize the session now.")
        #     ]
        # }

    def session_summary(self, state: AgentState):
        messages = state["messages"]
        response = self.llm.invoke(
            self.SESSION_SUMMARY_PROMPT.format(messages=messages)
        )
        result = response.content
        return {"messages": [AIMessage(content=result)]}

    def ask_new_question(self, state: AgentState):
        return {"messages": [AIMessage(content="What is your next question?")]}

    # update state of the graph for a specific thread
    def extend_duration(self, thread_id: str, extend_minutes: int):
        thread = {"configurable": {"thread_id": str(thread_id)}}
        current_duration = self.graph.get_state(thread).values["duration_minutes"]
        self.graph.update_state(
            thread, {"duration_minutes": current_duration + extend_minutes}
        )

    # helper function
    # def get_question_answer_context(self, messages: list):
    #     # Convert messages into conversation format
    #     conversation = []
    #     for msg in messages:
    #         if isinstance(msg, AIMessage):
    #             conversation.append(f"AI: {msg.content}")
    #         elif isinstance(msg, HumanMessage):
    #             conversation.append(f"Human: {msg.content}")

    #     return "\n".join(conversation)
