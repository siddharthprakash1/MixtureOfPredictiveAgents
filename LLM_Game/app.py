import streamlit as st
from dotenv import load_dotenv
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# Define the list of models
models = [
    "pxlksr/opencodeinterpreter-ds",
    "llama3",
    "llava",
    "qwen2",
    "deepseek-coder-v2",
    "codellama",
    "mistral"
]

# Streamlit UI
st.title("AI Question-Guessing Game")

st.sidebar.header("Choose your models")
model1_name = st.sidebar.selectbox("Model 1", models)
model2_name = st.sidebar.selectbox("Model 2", models)

class Player:
    def __init__(self, model):
        self.observations = []
        self.model = model
        self.concept = None
        self.history = []

    def initialize_host(self):
        template = """
        You are the host of a game where a player asks questions about
        a thing to guess what it is.

        Write the name of a thing. It must be a common object.
        It must be a single word. Do not write anything else. 
        Only write the name of the thing with no punctuation.

        Here is a list of things you cannot use:
        {history}
        """
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.model | StrOutputParser()

        self.concept = chain.invoke({"history": "\n".join(self.history)})
        self.history.append(self.concept)

        st.write(f"Concept: {self.concept}")

    def initialize_player(self):
        self.observations = []

    def ask(self, questions_left):
        template = """
        You are a player in a game where you need to ask Yes/No questions about 
        a thing and guess what it is.

        The thing is a common object. It is a single word.

        Here are the questions you have already asked:

        {observations}

        You only have {questions_left} questions left to ask. You want to guess
        in as few questions as possible. If there's only 1 question left, 
        you must make a guess or you'll lose the game. Be aggressive and try to
        guess the thing as soon as possible.

        Do not ask questions that you have already asked before.

        Only binary questions are allowed. The question must be answered
        with a Yes/No.
         
        Be as concise as possible when asking a question. Do not announce that you
        will ask the question. Do not say "Let's get started", or introduce your 
        question. Just write the question.

        Questions you have already asked:
        {observations}
        """
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.model | StrOutputParser()

        question = chain.invoke({
            "observations": "\n".join(self.observations),
            "questions_left": questions_left,
        })

        return question

    def answer(self, question):
        template = """
        You are the host of a game where a player asks questions about a thing 
        to guess what it is.

        The thing is a common object. It is a single word.

        Here is the question you need to answer:

        {question}

        Answer Yes or No. If the player has guessed the thing correctly, write
        "You've guessed it! The thing is {concept}." where {concept} is the 
        thing the player is trying to guess.

        Only provide the answer without any additional comments or phrases.
        """
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.model | StrOutputParser()

        answer = chain.invoke({"question": question, "concept": self.concept})

        return answer

    def add_observation(self, question, answer):
        self.observations.append(f"{question}: {answer}")

class Game:
    def __init__(self, model1, model2, rounds=3, questions=20):
        self.model1 = model1
        self.model2 = model2
        self.rounds = rounds
        self.questions = questions
        self.players = {
            "0": {
                "player": Player(model=self.model1),
                "score": 0,
            },
            "1": {
                "player": Player(model=self.model2),
                "score": 0,
            },
        }
        self.host_index = 0
        self.round = 0

    def start(self):
        for round in range(self.rounds):
            self.round += 1
            st.write(f"\nRound {self.round}. Player {self.host_index + 1} is the host.")

            player_index = 1 - self.host_index
            if self._play(
                self.players[str(self.host_index)]["player"], self.players[str(player_index)]["player"]
            ):
                st.write(f"Player {player_index + 1} guessed correctly.")
                self.players[str(player_index)]["score"] += 1
            else:
                st.write(f"Player {player_index + 1} didn't guess correctly.")
                self.players[str(self.host_index)]["score"] += 1

            self.host_index = 1 - self.host_index

        st.write("Final score:")
        st.write(f"Player 1: {self.players['0']['score']}")
        st.write(f"Player 2: {self.players['1']['score']}")

    def _play(self, host, player):
        host.initialize_host()
        player.initialize_player()
        for question_index in range(self.questions):
            question = player.ask(self.questions - question_index)
            answer = host.answer(question)

            st.write(f"Question {question_index + 1}: {question}. Answer: {answer}")

            player.add_observation(question, answer)

            if "guessed it" in answer.lower():
                st.write(answer)
                return True

        return False

if st.sidebar.button("Start Game"):
    game = Game(
        model1=Ollama(model=model1_name),
        model2=Ollama(model=model2_name),
        rounds=7,
    )
    game.start()

    # Display the leaderboard
    st.sidebar.subheader("Leaderboard")
    st.sidebar.write(f"Player 1 ({model1_name}): {game.players['0']['score']} points")
    st.sidebar.write(f"Player 2 ({model2_name}): {game.players['1']['score']} points")
