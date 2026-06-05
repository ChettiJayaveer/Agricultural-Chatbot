import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. Load Environment Variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# --- CONFIGURATION ---
DB_DIR = "vector_db"
DATA_DIR = "data"
# Using HuggingFace wrapper for sentence-transformers
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def format_docs(docs):
    """Joins retrieved PDF sections into a single string for the AI."""
    return "\n\n".join(doc.page_content for doc in docs)

def initialize_bot():
    """
    Builds the RAG logic using LCEL Pipes to avoid 'langchain.chains' errors.
    """
    # Load or Create Vector Database
    if os.path.exists(DB_DIR):
        vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    else:
        documents = []
        if os.path.exists(DATA_DIR) and os.listdir(DATA_DIR):
            for file in os.listdir(DATA_DIR):
                if file.endswith(".pdf"):
                    loader = PyPDFLoader(os.path.join(DATA_DIR, file))
                    documents.extend(loader.load())
        
        if not documents:
            # Fallback document to prevent initialization crashes
            from langchain_core.documents import Document
            texts = [Document(page_content="Agrigenius: Expert Agricultural AI.")]
        else:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_documents(documents)
            
        vector_db = Chroma.from_documents(
            documents=texts, 
            embedding=embeddings, 
            persist_directory=DB_DIR
        )

    retriever = vector_db.as_retriever(search_kwargs={"k": 3})
    
    # Initialize Gemini 2.5 Flash
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=API_KEY, 
        temperature=0.3
    )

    # --- STRICT AGRICULTURAL SYSTEM PROMPT ---
    system_prompt = (
        "You are 'Agrigenius AI', a professional agricultural expert. "
        "Your mission is to assist farmers with crops, soil, pests, and irrigation. "
        "\n\n"
        "STRICT OPERATING RULES:\n"
        "1. Answer ONLY questions related to agriculture and farming.\n"
        "2. If the user asks about MOVIES, SPORTS (like IPL), CELEBRITIES, or any NON-FARMING topic, "
        "you MUST NOT answer. Instead, say: 'I am Agrigenius, your dedicated farming assistant. "
        "I only provide information related to agriculture. How are your crops doing today?'\n"
        "\n\n"
        "CONTEXT: {context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # --- THE MODERN LCEL PIPE ---
    # This chain replaces create_retrieval_chain and create_stuff_documents_chain.
    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

# Initialize bot executor once at startup
bot_executor = initialize_bot()

def get_response(user_query):
    """
    Invokes the modern RAG pipe and returns the agricultural answer.
    """
    try:
        # LCEL 'invoke' returns the final string directly
        return bot_executor.invoke(user_query)
    except Exception as e:
        print(f"Chatbot Error: {e}")
        return "I am having trouble accessing my farming manuals. Please check your data folder."