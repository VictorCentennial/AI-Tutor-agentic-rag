# Import LangChain components
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import logging

# from langchain.document_loaders import TextLoader
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableSequence
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ChatMessage
import matplotlib

matplotlib.use("Agg")  # Use the 'Agg' backend
import matplotlib.pyplot as plt
import pandas as pd


# from langgraph.checkpoint.sqlite import SqliteSaver
# from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.memory import MemorySaver

from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt

from typing_extensions import TypedDict, Literal
from typing import Annotated, List
from datetime import timedelta, datetime
from langchain.schema import Document
from langchain.vectorstores.base import VectorStore
from rag import rag
import logging

from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Any, Optional

from flask import current_app
from langchain_core.runnables.config import RunnableConfig


class AgentState(TypedDict):
    subject: str
    topic: str
    week_selected: List[int]
    titles: List[str]
    summary: str
    messages: Annotated[list, add_messages]
    answer_trials: int
    start_time: datetime
    duration_minutes: int
    tutor_question: str
    student_question: str
    task_breakdown: List[str]
    current_task_index: int  # index of the current task
    task_solving_start_index: int  # index of the first task that the student is solving
    vector_store_paths: List[str]
    current_week: int
    use_mongodb_vector_store: bool


class AiTutorAgent:

    # Maximum number of attempts a student can make to answer a question
    # before the system provides a complete explanation
    MAX_ANSWER_ATTEMPTS: int = 3

    def __init__(
        self,
        GOOGLE_MODEL_NAME: str,
        GOOGLE_API_KEY: str,
        memory: MemorySaver,
        vector_store: Optional[VectorStore] = None,
    ):
        self.llm = ChatGoogleGenerativeAI(
            model=GOOGLE_MODEL_NAME, google_api_key=GOOGLE_API_KEY
        )
        self.memory = memory
        self.vector_store = vector_store

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
        # builder.add_node("add_wrong_answer_trials", self.add_wrong_answer_trials)
        builder.add_node(
            "tell_student_answer_is_correct", self.tell_student_answer_is_correct
        )
        builder.add_node("hints", self.hints)
        builder.add_node("explain_answer", self.explain_answer)
        builder.add_node("intermediate_summary", self.intermediate_summary)
        # builder.add_node("ask_any_further_question", self.ask_any_further_question)
        builder.add_node(
            "student_answer_if_any_further_question",
            self.student_answer_if_any_further_question,
        )
        builder.add_node("session_summary", self.session_summary)

        # for task type question
        builder.add_node("time_out_message", self.time_out_message)
        builder.add_node("question_breakdown", self.question_breakdown)
        builder.add_node("subtask_guideline", self.subtask_guideline)
        builder.add_node("student_answer_subtask", self.student_answer_subtask)
        builder.add_node("check_subtask_answer", self.check_subtask_answer)
        builder.add_node("hint_for_subtask", self.hint_for_subtask)
        builder.add_node("explain_subtask_answer", self.explain_subtask_answer)
        builder.add_node("task_solving_summary", self.task_solving_summary)

        builder.add_edge(START, "create_summary")

        self.graph = builder.compile(
            checkpointer=memory,
            # interrupt_before=[
            #     "student_input",
            #     "student_answer_question",
            #     "student_answer_if_any_further_question",
            # ],
        )

        self.SUMMARY_PROMPT = """
            Generate a concise summary of the key topics present in the provided titles. 
            List a few key topics in bullet points.

            titles: {titles}
        """

        self.GREETING_PROMPT = """
            You are an AI Tutor. You are given a subject and a topic with its content summary.
            If the topics is not provided, then ignore topics and provide possible topics based on the subject.

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
            - If the student's question is not related to the topic, respond with **"Fail"**.
            - If the student's question is related to the topic, 
                then if the question is a generalknowledge question, respond with **"Pass"**.
                else if the question is a question which involves solving problem (e.g. question from assignemnt), respond with **"Question"**.

            3. **Note**:
            - Provide only the one-word response ("Pass" or "Fail" or "Question") without any additional comments.

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

        self.QUESTION_BREAKDOWN_PROMPT = """
            You are an AI Tutor.

            **Instructions**:

            Read the student's question carefully.
            Decompose the question into a two to three smaller, manageable tasks that the student can tackle one by one.
            Express each task in clear, student-friendly language.
            If possible, tasks should be based on the related course content.
            Separate each task with a vertical bar (|). The entire response must be a single line with no line breaks.
            Example Output:
            create a Car class with attributes | create a getter and setter for each attribute | create a method to display all the attributes of the Car class

            **Student's Question**:
            {question}
            
            **Related Course Content**:
            {related_course_content}
        """

        self.SHOW_SUBTASK_PROMPT = "In order to solve the task, you need to solve the following subtasks:\n{task_list}"

        self.SUBTASK_GUIDELINE_PROMPT = """
            You are an AI Tutor.

            **Instructions**:
            You are guiding the student to solve done of a series of subtasks that are part of a larger task. 
            The student is currently working on the given subtask.
            
            For the given subtask, profile a guideline for the student to solve the subtask.
            The guideline should be concise and to the point.
            The guideline should be written in a way that is easy for the student to understand.
            
            When referring to code elements like class names, methods, or keywords:
            - Use 'code' formatting for class names, methods, and code keywords
            - Avoid using backticks in the explanation text
            - Use bold or italics for emphasis instead
            

            DO NOT solve the subtask yourself. You can give the student some initial guidance. 
            Let the student to work on the subtask.
            
            Refer to the related course content to provide the guideline if applicable.
            Also refer to the previous conversation with the student to provide the guideline if applicable 
            and ensure smooth transaction to this subtask.
           
            **Subtask**:
            {task}
            
            **Related Course Content**:
            {related_course_content}
            
            **Previous Conversation**:
            {previous_conversation}
        """

        self.CHECK_SUBTASK_ANSWER_PROMPT = """
            You are an AI Tutor.

            **Instructions**:
            Evaluate the student's answer to the subtask, based on the student's answer and the results from previous subtasks.
            If the answer is correct, respond with **"Correct"**.
            If the answer is incorrect, respond with **"Wrong"**.
            Provide a one-word response ("Correct" or "Wrong") without any additional hints or feedback.

            **Subtask**:
            {task}
            
            **Student's Answer**:
            {student_answer}
            
            **Previous Subtask history**:
            {previous_subtask_history}
        """

        self.HINT_FOR_SUBTASK_PROMPT = """

            You are an AI Tutor.

            **Instructions**:
            Student try to solve the subtask but failed.
            Please check what is the problem and provide a hint to the student to solve the subtask.
            
            **Subtask**:
            {task}
            
            **Student's Answer**:
            {student_answer}
            
            **Previous Conversation**:
            {previous_conversation}
        """

        self.EXPLAIN_SUBTASK_ANSWER_PROMPT = """
            You are an AI Tutor.

            **Instructions**:
            Student try to solve the subtask but failed.
            Please check what is the problem and provide a explanation to the student to solve the subtask.
            Also provide the student the related course content to solve the subtask.
            Explain the answer in a way that is easy for the student to understand.
            Use the related course content to explain the answer if applicable.
                        
            **Subtask**:
            {task}
            
            **Student's Answer Attempt**:
            {student_answer_attempt}
            
            **Related Course Content**:
            {related_course_content}
        """

        self.TASK_SOLVING_SUMMARY_PROMPT = """
            You are an AI Tutor.

            **Instructions**:
            Summarize the student's progress in solving the task.
            Highlight the key concepts and ideas that the student has learned or improved upon.
            Explain about how the subtask are related to the overall task.
            Connect all the subtasks to form the overall task. 
            
            Explain how the task is being solved by the student.
            Reflect on the student's misconceptions and mistakes in the progress on solving tasks

            **Task**:
            {task}
            
            **Subtasks**:
            {subtasks}

            **Student's progress**:
            {student_progress}

        """

    def general_analysis(self, combined_content: str, session_data: list[dict]):
        return self._generate_analysis(
            "General Analysis", combined_content, session_data
        )

    def student_analysis(
        self, student_id: str, combined_content: str, session_data: list[dict]
    ):
        return self._generate_analysis(
            f"Student {student_id} Analysis", combined_content, session_data
        )

    def course_analysis(
        self, course_code: str, combined_content: str, session_data: list[dict]
    ):
        return self._generate_analysis(
            f"Course {course_code} Analysis", combined_content, session_data
        )

    def day_analysis(self, date: str, combined_content: str, session_data: list[dict]):
        return self._generate_analysis(
            f"Day {date} Analysis", combined_content, session_data
        )

    def _generate_analysis(self, title: str, content: str, session_data: list[dict]):
        # Customize the prompt based on the type of analysis
        if "General Analysis" in title:
            prompt = f"""
                Analyze the following session data for {title}:
                {content}

                Provide a detailed summary of:
                1. Key insights across all sessions.
                2. Common patterns or trends.
                3. Overall performance metrics.
            """
        elif "Student" in title:
            prompt = f"""
                Analyze the following session data for {title}:
                {content}

                Provide a detailed summary of:
                1. Key insights for this student.
                2. Performance trends.
                3. Areas of improvement.
            """
        elif "Course" in title:
            prompt = f"""
                Analyze the following session data for {title}:
                {content}

                Provide a detailed summary of:
                1. Key insights for this course.
                2. Common challenges faced by students.
                3. Overall course performance.
            """
        elif "Day" in title:
            prompt = f"""
                Analyze the following session data for {title}:
                {content}

                Provide a detailed summary of:
                1. Key insights for this day.
                2. Session activity trends.
                3. Notable events or issues.
            """
        else:
            prompt = f"""
                Analyze the following session data:
                {content}

                Provide a summary of:
                1. Key insights.
                2. Trends and patterns.
                3. Performance metrics.
            """

        if content == "":
            return {"summary": "No history available", "visualizations": {}}

        # Generate analysis using LLM
        response = self.llm.invoke(prompt)

        # Generate visualizations based on session data
        visualizations = self._generate_visualizations(title, session_data)

        return {"summary": response.content, "visualizations": visualizations}

    def _generate_visualizations(self, title: str, session_data: list[dict]):
        try:
            logging.info(f"Generating visualizations for: {title}")

            # Ensure the visualizations directory exists
            if not os.path.exists("static/visualizations"):
                os.makedirs("static/visualizations")

            # # Get session data
            # session_files = self._get_all_session_files()
            # session_data = []

            # for filepath in session_files:
            #     filename = os.path.basename(filepath)
            #     parts = filename.split("_")
            #     if len(parts) == 4:
            #         date, time, course_code, student_id = parts
            #         student_id = student_id.split(".")[0]  # Remove .txt
            #         session_data.append(
            #             {
            #                 "date": date,
            #                 "time": time,
            #                 "course_code": course_code,
            #                 "student_id": student_id,
            #             }
            #         )

            # Convert session data to a DataFrame
            df = pd.DataFrame(session_data)

            # Generate visualizations based on the type of analysis
            if "Student" in title:
                student_id = title.replace("Student ", "").replace(" Analysis", "")
                student_sessions = df[df["student_id"] == student_id]

                # Bar graph: Sessions per date
                session_counts = student_sessions["date"].value_counts().sort_index()
                plt.figure(figsize=(10, 6))
                session_counts.plot(kind="bar", color="skyblue")
                plt.title(f"Sessions for Student {student_id}")
                plt.xlabel("Date")
                plt.ylabel("Number of Sessions")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                plt.savefig(f"static/visualizations/{title}_sessions_bar.png")
                plt.close()

                # Pie chart: Sessions per course
                course_counts = student_sessions["course_code"].value_counts()
                plt.figure(figsize=(8, 8))
                course_counts.plot(
                    kind="pie",
                    autopct="%1.1f%%",
                    colors=["lightgreen", "lightcoral", "lightskyblue"],
                )
                plt.title(f"Course Distribution for Student {student_id}")
                plt.ylabel("")
                plt.savefig(f"static/visualizations/{title}_courses_pie.png")
                plt.close()

                return {
                    "sessions_bar_chart": f"visualizations/{title}_sessions_bar.png",
                    "courses_pie_chart": f"visualizations/{title}_courses_pie.png",
                }

            elif "Course" in title:
                course_code = title.replace("Course ", "").replace(" Analysis", "")
                course_sessions = df[df["course_code"] == course_code]

                # Line graph: Sessions over time
                session_counts = course_sessions["date"].value_counts().sort_index()
                plt.figure(figsize=(10, 6))
                session_counts.plot(kind="line", marker="o", color="purple")
                plt.title(f"Sessions for Course {course_code}")
                plt.xlabel("Date")
                plt.ylabel("Number of Sessions")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()

                # Replace spaces with underscores in the title for the filename
                filename = title.replace(" ", "_")
                plt.savefig(f"static/visualizations/{filename}_sessions_line.png")
                plt.close()

                # Bar graph: Sessions per student
                student_counts = course_sessions["student_id"].value_counts()
                plt.figure(figsize=(10, 6))
                student_counts.plot(kind="bar", color="orange")
                plt.title(f"Student Participation in Course {course_code}")
                plt.xlabel("Student ID")
                plt.ylabel("Number of Sessions")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                plt.savefig(f"static/visualizations/{filename}_students_bar.png")
                plt.close()

                return {
                    "sessions_line_chart": f"visualizations/{filename}_sessions_line.png",
                    "students_bar_chart": f"visualizations/{filename}_students_bar.png",
                }

            elif "Day" in title:
                date = title.replace("Day ", "").replace(" Analysis", "")
                day_sessions = df[df["date"] == date]

                # Pie chart: Sessions per course
                course_counts = day_sessions["course_code"].value_counts()
                plt.figure(figsize=(8, 8))
                course_counts.plot(
                    kind="pie",
                    autopct="%1.1f%%",
                    colors=["gold", "lightblue", "lightgreen"],
                )
                plt.title(f"Course Distribution on {date}")
                plt.ylabel("")
                plt.savefig(f"static/visualizations/{title}_courses_pie.png")
                plt.close()

                # Bar graph: Sessions per student
                student_counts = day_sessions["student_id"].value_counts()
                plt.figure(figsize=(10, 6))
                student_counts.plot(kind="bar", color="lightcoral")
                plt.title(f"Student Participation on {date}")
                plt.xlabel("Student ID")
                plt.ylabel("Number of Sessions")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                plt.savefig(f"static/visualizations/{title}_students_bar.png")
                plt.close()

                return {
                    "courses_pie_chart": f"visualizations/{title}_courses_pie.png",
                    "students_bar_chart": f"visualizations/{title}_students_bar.png",
                }

            else:  # General Analysis
                # Bar graph: Total sessions over time
                session_counts = df["date"].value_counts().sort_index()
                plt.figure(figsize=(10, 6))
                session_counts.plot(kind="bar", color="teal")
                plt.title("Total Sessions Over Time")
                plt.xlabel("Date")
                plt.ylabel("Number of Sessions")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                plt.savefig(f"static/visualizations/{title}_sessions_bar.png")
                plt.close()

                # Pie chart: Sessions per course
                course_counts = df["course_code"].value_counts()
                plt.figure(figsize=(8, 8))
                course_counts.plot(
                    kind="pie",
                    autopct="%1.1f%%",
                    colors=["lightpink", "lightblue", "lightgreen"],
                )
                plt.title("Course Distribution")
                plt.ylabel("")
                plt.savefig(f"static/visualizations/{title}_courses_pie.png")
                plt.close()

                return {
                    "sessions_bar_chart": f"visualizations/{title}_sessions_bar.png",
                    "courses_pie_chart": f"visualizations/{title}_courses_pie.png",
                }

        except Exception as e:
            logging.error(f"Error generating visualizations: {str(e)}")
            return {"error": "Failed to generate visualizations"}

    def retry_on_error(
        max_retries: int = 3,
        validator: Callable[[Any], bool] = None,
        error_goto: str = "student_input",
        error_message: str = "I apologize, but I'm having trouble processing your question. Could you please try again?",
    ):
        """
        Decorator for retrying agent methods on error or invalid output from LLM.

        Args:
            max_retries: Maximum number of retry attempts
            validator: Function to validate the output
            error_goto: Where to go if all retries fail
            error_message: Message to show user if all retries fail
        """
        # Type variables for generic function signature
        P = ParamSpec("P")
        R = TypeVar("R")

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                current_retry = 0
                last_error = None

                while current_retry < max_retries:
                    try:
                        result = func(*args, **kwargs)

                        # If no validator provided or validation passes, return result
                        if validator is None or validator(result):
                            return result

                        raise ValueError("Output validation failed")

                    except Exception as e:
                        current_retry += 1
                        last_error = e
                        logging.warning(
                            f"{func.__name__} - Attempt {current_retry}/{max_retries} failed: {str(e)}"
                        )

                # If all retries failed, return error Command
                logging.error(
                    f"{func.__name__} - All {max_retries} attempts failed. Last error: {str(last_error)}"
                )
                return Command(
                    update={"messages": [AIMessage(content=error_message)]},
                    goto=error_goto,
                )

            return wrapper

        return decorator

    def validate_task_breakdown(result: Command) -> bool:
        """Validates task breakdown output format"""
        if not isinstance(result, Command):
            return False

        state_update = result.update
        if "task_breakdown" not in state_update:
            return False

        tasks = state_update["task_breakdown"]
        # make sure at least break down into 2 tasks
        return len(tasks) > 1 and all(task.strip() for task in tasks)

    def create_summary(self, state: AgentState) -> Command[Literal["greeting"]]:

        response = self.llm.invoke(self.SUMMARY_PROMPT.format(titles=state["titles"]))
        # return {"summary": response.content}
        return Command(
            # state update
            update={"summary": response.content},
            # Control flow
            goto="greeting",
        )

    def greeting(self, state: AgentState) -> Command[Literal["student_input"]]:
        subject = state["subject"]
        summary = state["summary"]
        greeting_prompt = self.GREETING_PROMPT.format(subject=subject, summary=summary)
        messages = [HumanMessage(content=greeting_prompt)]
        response = self.llm.invoke(messages)
        # return {"messages": response}
        return Command(
            # state update
            update={"messages": response},
            # Control flow
            goto="student_input",
        )

    def student_input(self, state: AgentState) -> Command[
        Literal[
            "time_out_message",
            "reask_question",
            "llm_answer_question",
            "question_breakdown",
        ]
    ]:
        question = interrupt("Do you have any questions?")
        question_type_prompt = self.QUESTION_GUARDING_PROMPT.format(
            question=question, summary=state["summary"]
        )

        # TODO: add repeat mechanism for the question type prompt
        question_type_response = self.llm.invoke(question_type_prompt).content
        print(f"question_type_response: {question_type_response}")

        if self.time_out(state):
            goto = "time_out_message"
        elif question_type_response.startswith("Fail"):
            goto = "reask_question"
        elif question_type_response.startswith("Pass"):
            goto = "llm_answer_question"
        elif question_type_response.startswith("Question"):
            goto = "question_breakdown"

        else:
            logging.error(
                f"question_type_response not in expected format: {question_type_response}"
            )
            goto = END

        return Command(
            # state update
            update={
                "messages": [HumanMessage(content=question)],
                "student_question": question,
                # reset related variables
                "task_breakdown": [],
                "tutor_question": "",
                "answer_trials": 0,
            },
            # Control flow
            goto=goto,
        )

    # helper function
    def time_out(self, state: AgentState):
        current_time = datetime.now()
        start_time = state["start_time"]
        duration_minutes = state["duration_minutes"]
        return (current_time - start_time) > timedelta(minutes=duration_minutes)

    def reask_question(self, state: AgentState) -> Command[Literal["student_input"]]:
        return Command(
            # state update
            update={
                "messages": [
                    AIMessage(
                        content="Your question is not related to the topic. Please ask a question related to the topic."
                    )
                ]
            },
            # Control flow
            goto="student_input",
        )

    def llm_answer_question(
        self, state: AgentState, config: RunnableConfig
    ) -> Command[Literal["student_answer_question"]]:

        thread_id = config["metadata"]["thread_id"]
        if thread_id is None:
            raise ValueError("No thread_id in current context")

        while True:
            question = state["student_question"]

            result_from_document_search = self.vector_search(state, question, thread_id)
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
        return Command(
            # state update
            update={
                "messages": [AIMessage(content=result)],
                "answer_trials": 0,
                "tutor_question": tutor_question,
            },
            # Control flow
            goto="student_answer_question",
        )

    def student_answer_question(self, state: AgentState) -> Command[
        Literal[
            "time_out_message",
            "tell_student_answer_is_correct",
            "hints",
            "explain_answer",
        ]
    ]:
        # TODO: client to handle the interrupt value
        student_answer = interrupt("What is your answer?")

        if self.time_out(state):
            goto = "time_out_message"
        else:
            answer_trials = state["answer_trials"]
            question = state["tutor_question"]
            response = self.llm.invoke(
                self.CHECK_QUESTION_ANSWER_PROMPT.format(
                    question=question, answer=student_answer
                )
            )
            result = response.content.strip()
            # check if the answer is correct
            if result.lower().startswith("correct"):
                goto = "tell_student_answer_is_correct"
            else:
                # check if wrong answer exceeds the max answer attempts
                if answer_trials >= self.MAX_ANSWER_ATTEMPTS:
                    goto = "explain_answer"
                else:
                    goto = "hints"

        return Command(
            # state update
            update={"messages": [HumanMessage(content=student_answer)]},
            # Control flow
            goto=goto,
        )

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

    # def further_question_correctness(self, state: AgentState, max_trials=3):
    #     if self.time_out(state):
    #         return "TimeOut"

    #     answer_trials = state["answer_trials"]
    #     if answer_trials >= max_trials:
    #         return "Stop"

    #     answer = state["messages"][-1].content
    #     question = state["tutor_question"]

    #     response = self.llm.invoke(
    #         self.CHECK_QUESTION_ANSWER_PROMPT.format(question=question, answer=answer)
    #     )

    #     result = response.content.strip()
    #     return "Correct" if result.lower().startswith("correct") else "Wrong"
    #     # need to add one trials for answer_trials

    def tell_student_answer_is_correct(
        self, state: AgentState
    ) -> Command[Literal["intermediate_summary"]]:
        return Command(
            # state update
            update={"messages": [AIMessage(content="Your answer is correct.")]},
            # Control flow
            goto="intermediate_summary",
        )

    # def add_wrong_answer_trials(self, state: AgentState):
    #     return {"answer_trials": state["answer_trials"] + 1}

    def hints(self, state: AgentState) -> Command[Literal["student_answer_question"]]:
        question_answer_context = self.get_question_answer_context(state)
        print(f"question_answer_context for hints: {question_answer_context}")
        response = self.llm.invoke(
            self.HINTS_PROMPT.format(question_answer_context=question_answer_context)
        )
        result = response.content
        # return {"messages": [AIMessage(content=result)]}
        return Command(
            # state update (add one trials for answer_trials and update the messages with the hints)
            update={
                "answer_trials": state["answer_trials"] + 1,
                "messages": [AIMessage(content=result)],
            },
            # Control flow
            goto="student_answer_question",
        )

    def explain_answer(
        self, state: AgentState
    ) -> Command[Literal["intermediate_summary"]]:
        question_answer_context = self.get_question_answer_context(state)
        response = self.llm.invoke(
            self.EXPLAIN_ANSWER_PROMPT.format(
                question_answer_context=question_answer_context
            )
        )
        result = response.content
        # return {"messages": [AIMessage(content=result)]}
        return Command(
            # state update
            update={"messages": [AIMessage(content=result)]},
            # Control flow
            goto="intermediate_summary",
        )

    def intermediate_summary(
        self, state: AgentState
    ) -> Command[Literal["student_answer_if_any_further_question"]]:
        question_answer_context = self.get_question_answer_context(state)
        response = self.llm.invoke(
            self.INTERMEDIATE_SUMMARY_PROMPT.format(
                question_answer_context=question_answer_context
            )
        )
        result = response.content
        # return {"messages": [AIMessage(content=result)]}
        return Command(
            # state update
            update={
                "messages": [
                    AIMessage(content=result),
                    # ask student if they have any further question
                    AIMessage(content=self.ANY_FURTHER_QUESTION_PROMPT),
                ]
            },
            # Control flow
            goto="student_answer_if_any_further_question",
        )

    # def ask_any_further_question(self, state: AgentState):
    #     return {"messages": [AIMessage(content=self.ANY_FURTHER_QUESTION_PROMPT)]}

    def student_answer_if_any_further_question(
        self, state: AgentState
    ) -> Command[Literal["session_summary", "student_input"]]:
        update = {}

        # if time out, go to session summary
        if self.time_out(state):
            # Control flow
            goto = "time_out_message"
        else:

            # if student answer is yes, go to student input
            student_answer = interrupt("Do you have any further question?")

            if student_answer.lower().startswith("yes"):

                # state update
                update = {
                    "messages": [
                        HumanMessage(content=student_answer),
                        AIMessage(content="What is your next question?"),
                    ]
                }
                # Control flow
                goto = ("student_input",)
            else:
                # Control flow
                goto = "session_summary"

        return Command(
            # state update
            update=update,
            # Control flow
            goto=goto,
        )

    # def any_further_question(self, state: AgentState):
    #     if self.time_out(state):
    #         return "TimeOut"
    #     student_answer = state["messages"][-1].content
    #     return student_answer

    # response = self.llm.invoke(
    #     self.ANY_FURTHER_QUESTION_PROMPT.format(student_answer=student_answer)
    # )
    # result = response.content
    # if result.startswith("Yes"):
    #     return "Yes"
    # else:
    #     return "No"

    def time_out_message(
        self, state: AgentState
    ) -> Command[Literal["session_summary"]]:
        return Command(
            # state update
            update={
                "messages": [
                    AIMessage(content="Time is up. We will summarize the session now.")
                ]
            },
            # Control flow
            goto="session_summary",
        )
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
        # return {"messages": [AIMessage(content=result)]}
        return Command(
            # state update
            update={"messages": [AIMessage(content=result)]},
            # Control flow
            goto=END,
        )

    @retry_on_error(validator=validate_task_breakdown)
    def question_breakdown(
        self, state: AgentState, config: RunnableConfig
    ) -> Command[Literal["subtask_guideline"]]:
        question = state["student_question"]

        # Extract thread_id from config
        thread_id = config["metadata"]["thread_id"]
        if thread_id is None:
            raise ValueError("No thread_id in current context")

        related_course_content = self.vector_search(state, question, thread_id)
        response = self.llm.invoke(
            self.QUESTION_BREAKDOWN_PROMPT.format(
                question=question, related_course_content=related_course_content
            )
        )
        result = response.content
        task_breakdown = [task.strip() for task in result.split("|")]
        task_breakdown_list_str = "\n".join(
            [f"{i+1}. {task}" for i, task in enumerate(task_breakdown)]
        )
        print(task_breakdown_list_str)
        task_breakdown_str = self.SHOW_SUBTASK_PROMPT.format(
            task_list=task_breakdown_list_str
        )
        logging.info(f"task_breakdown: {task_breakdown}")

        print(task_breakdown_str)

        return Command(
            # state update
            update={
                "messages": [AIMessage(content=task_breakdown_str)],
                "task_breakdown": task_breakdown,
                "task_solving_start_index": len(state["messages"]) - 1,
            },
            # Control flow
            goto="subtask_guideline",
        )

    def subtask_guideline(
        self, state: AgentState, config: RunnableConfig
    ) -> Command[Literal["student_answer_subtask"]]:
        task_breakdown = state["task_breakdown"]
        current_task_index = state["current_task_index"]
        current_task = task_breakdown[current_task_index]

        # Extract thread_id from config
        thread_id = config["metadata"]["thread_id"]
        if thread_id is None:
            raise ValueError("No thread_id in current context")

        vector_search_results = self.vector_search(state, current_task, thread_id)
        previous_conversation = state["messages"][state["task_solving_start_index"] :]
        response = self.llm.invoke(
            self.SUBTASK_GUIDELINE_PROMPT.format(
                task=current_task,
                related_course_content=vector_search_results,
                previous_conversation=previous_conversation,
            )
        )
        result = response.content
        subtask_guideline_str = (
            f"**Subtask {current_task_index + 1}: {current_task}**\n{result}"
        )

        return Command(
            # state update
            update={"messages": [AIMessage(content=subtask_guideline_str)]},
            # Control flow
            goto="student_answer_subtask",
        )

    def student_answer_subtask(
        self, state: AgentState
    ) -> Command[Literal["check_subtask_answer"]]:
        update = {}
        if self.time_out(state):
            # Control flow
            goto = "time_out_message"
        else:
            student_answer = interrupt("What is your answer?")
            update = {"messages": [HumanMessage(content=student_answer)]}
            goto = "check_subtask_answer"

        return Command(
            # state update
            update=update,
            # Control flow
            goto=goto,
        )

    def check_subtask_answer(self, state: AgentState) -> Command[
        Literal[
            "task_solving_summary",
            "subtask_guideline",
            "hint_for_subtask",
            "explain_subtask_answer",
        ]
    ]:
        student_answer = state["messages"][-1].content
        current_task_index = state["current_task_index"]
        current_task = state["task_breakdown"][current_task_index]
        task_solving_start_index = state["task_solving_start_index"]
        previous_subtask_history = state["messages"][task_solving_start_index:]

        response = self.llm.invoke(
            self.CHECK_SUBTASK_ANSWER_PROMPT.format(
                student_answer=student_answer,
                task=current_task,
                previous_subtask_history=previous_subtask_history,
            )
        )

        result = response.content
        if result.lower().startswith("correct"):
            if state["current_task_index"] == len(state["task_breakdown"]) - 1:
                update = {
                    "messages": [AIMessage(content="You have solved all the tasks.")],
                    "answer_trials": 0,
                    "current_task_index": 0,
                }
                goto = "task_solving_summary"
            else:
                update = {
                    "current_task_index": current_task_index + 1,
                    "answer_trials": 0,
                }
                goto = "subtask_guideline"
        else:
            if state["answer_trials"] >= self.MAX_ANSWER_ATTEMPTS:
                update = {"answer_trials": 0}
                goto = "explain_subtask_answer"
            else:
                update = {
                    "answer_trials": state["answer_trials"] + 1,
                }
                goto = "hint_for_subtask"

        return Command(
            # state update
            update=update,
            # Control flow
            goto=goto,
        )

    def hint_for_subtask(
        self, state: AgentState
    ) -> Command[Literal["student_answer_subtask"]]:
        response = self.llm.invoke(
            self.HINT_FOR_SUBTASK_PROMPT.format(
                task=state["task_breakdown"][state["current_task_index"]],
                student_answer=state["messages"][-1].content,
                previous_conversation=state["messages"][
                    state["task_solving_start_index"] :
                ],
            )
        )
        result = response.content
        return Command(
            # state update
            update={"messages": [AIMessage(content=result)]},
            # Control flow
            goto="student_answer_subtask",
        )

    def explain_subtask_answer(
        self, state: AgentState, config: RunnableConfig
    ) -> Command[Literal["task_solving_summary", "subtask_guideline"]]:
        current_task_index = state["current_task_index"]
        task_breakdown = state["task_breakdown"]
        current_task = task_breakdown[current_task_index]
        student_subtask_start_index = -2 * (self.MAX_ANSWER_ATTEMPTS)
        student_answer_attempt = state["messages"][student_subtask_start_index:]

        # Extract thread_id from config
        thread_id = config["metadata"]["thread_id"]
        if thread_id is None:
            raise ValueError("No thread_id in current context")

        related_course_content = self.vector_search(state, current_task, thread_id)

        response = self.llm.invoke(
            self.EXPLAIN_SUBTASK_ANSWER_PROMPT.format(
                task=current_task,
                student_answer_attempt=student_answer_attempt,
                related_course_content=related_course_content,
            )
        )
        result = response.content

        if current_task_index >= len(task_breakdown) - 1:
            update = {
                "messages": [AIMessage(content=result)],
                "answer_trials": 0,
                "current_task_index": 0,
            }
            goto = "task_solving_summary"
        else:
            update = {
                "current_task_index": current_task_index + 1,
                "answer_trials": 0,
            }
            goto = "subtask_guideline"

        return Command(
            # state update
            update=update,
            # Control flow
            goto=goto,
        )

    def task_solving_summary(
        self, state: AgentState
    ) -> Command[Literal["student_answer_if_any_further_question"]]:
        messages = state["messages"]
        task_solving_start_index = state["task_solving_start_index"]
        previous_conversation = messages[task_solving_start_index:]

        response = self.llm.invoke(
            self.TASK_SOLVING_SUMMARY_PROMPT.format(
                task=state["student_question"],
                subtasks=state["task_breakdown"],
                student_progress=previous_conversation,
            )
        )
        result = response.content

        return Command(
            # state update
            update={
                "messages": [
                    AIMessage(content=result),
                    AIMessage(content=self.ANY_FURTHER_QUESTION_PROMPT),
                ],
                "student_question": "",
                "task_breakdown": [],
                "task_solving_start_index": 0,
            },
            # Control flow
            goto="student_answer_if_any_further_question",
        )

    # update state of the graph for a specific thread
    def extend_duration(self, thread_id: str, extend_minutes: int):
        thread = {"configurable": {"thread_id": str(thread_id)}}
        current_duration = self.graph.get_state(thread).values["duration_minutes"]
        self.graph.update_state(
            thread, {"duration_minutes": current_duration + extend_minutes}
        )

    def vector_search(
        self, state: AgentState, question: str, thread_id: str, k: int = 3
    ) -> str:
        """
        Search the vector store for documents related to the query.

        Args:
            question (str): The search query
            thread_id (str): The thread ID to identify which vector store to use
            k (int, optional): Number of documents to return. Defaults to 3.

        Returns:
            str: Combined content from matching documents

        Raises:
            ValueError: If vector store not found for the thread_id
        """

        try:

            # Perform the search
            if state["use_mongodb_vector_store"]:
                vector_search_results = self.vector_store.similarity_search_with_score(
                    question,
                    k=k,
                    pre_filter={
                        "course": {"$eq": state["subject"]},
                        "week": {"$in": state["week_selected"]},
                    },
                )
                print(vector_search_results)
                # Sort by score (highest first)
                sorted_results = sorted(
                    vector_search_results, key=lambda x: x[1], reverse=True
                )

                # Join with score and metadata
                vector_search_results_str = "\n\n".join(
                    [
                        f"**{doc.metadata['title']}** (Score: {score:.4f})\n"
                        f"Course: {doc.metadata.get('course', 'Unknown')}, "
                        f"Week: {doc.metadata.get('week', 'Unknown')}\n"
                        f"{doc.page_content}"
                        for doc, score in sorted_results
                    ]
                )
            else:
                if not hasattr(current_app, "vector_stores"):
                    raise ValueError(
                        "Flask app does not have vector_stores dictionary initialized"
                    )

                if thread_id not in current_app.vector_stores:
                    # Try to get thread state to provide more informative error
                    thread = {"configurable": {"thread_id": str(thread_id)}}
                    state = self.graph.get_state(thread)

                    try:
                        subject = state.values.get("subject", "unknown")
                        current_week = state.values.get("current_week", "unknown")
                        has_paths = "vector_store_paths" in state.values
                        raise ValueError(
                            f"No vector store found for thread {thread_id}. "
                            f"Subject: {subject}, Week: {current_week}, "
                            f"Has paths: {has_paths}. The session may have expired."
                        )
                    except Exception as inner_e:
                        # Fall back to simpler error if we can't get state info
                        raise ValueError(
                            f"No vector store found for thread {thread_id}. The session may have expired."
                        )

                local_vector_store = current_app.vector_stores[thread_id]
                vector_search_results = local_vector_store.similarity_search(
                    question, k=k
                )

                # Clean up the results before joining
                vector_search_results_str = (
                    "\n\n".join(
                        " ".join(doc.page_content.split())  # Clean up extra spaces
                        for doc in vector_search_results
                    )
                    if vector_search_results
                    else "No related content"
                )

            logging.info(f"vector_search_results_str: {vector_search_results_str}")
            return vector_search_results_str

        except ValueError as e:
            # Re-raise value errors with the original message
            raise e
        except Exception as e:
            # For other errors, provide more context
            logging.error(f"Error in vector_search: {str(e)}")
            raise ValueError(f"Failed to search vector store: {str(e)}")
