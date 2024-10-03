import os
import time
from typing import  List

from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.vectorstores import Chroma

# Configuration
DOCUMENT_DIR = "documents"
DB_DIR = "vectorstore"
CHECK_INTERVAL = 600  # seconds
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.1:latest"


from langchain.schema import Document


def load_and_process_documents(directory: str) -> tuple[List[Document], List[Document]]:
    """Load documents from a directory and process them."""
    documents = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    documents.append(
                        Document(page_content=content, metadata={"source": file_path})
                    )
                except Exception as e:
                    print(f"Error loading file {file_path}: {str(e)}")

    if not documents:
        print(f"No valid documents found in {directory}")
        return None

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )

    chunks = text_splitter.split_documents(documents)
    return chunks, documents


def contextual_chunking(
    chunks: List[Document], documents: List[Document], llm
) -> List[Document]:
    """Perform contextual chunking using a local LLM."""
    prompt_template = """
    <document> 
    {{full_doc}} 
    </document> 
    Here is the chunk we want to situate within the whole document 
    <chunk> 
    {{chunk}} 
    </chunk> 
    Please give a short succinct context to situate this chunk within the overall 
    document for the purposes of improving search retrieval of the chunk. 
    Answer only with the succinct context and nothing else.
    """
    prompt = PromptTemplate(
        template=prompt_template, input_variables=["full_doc", "chunk"]
    )

    contextual_chunks = []
    for chunk in chunks:
        # Find the corresponding full document for this chunk
        full_doc = next(
            (
                doc.page_content
                for doc in documents
                if doc.metadata["source"] == chunk.metadata["source"]
            ),
            "",
        )

        context = llm.invoke(prompt.format(full_doc=full_doc, chunk=chunk.page_content))
        contextual_chunks.append(
            Document(
                page_content=f"Context: {context}\n\nChunk: {chunk.page_content}",
                metadata=chunk.metadata,
            )
        )

    return contextual_chunks


def create_and_store_embeddings(chunks: List[Document]) -> Chroma:
    """Create embeddings and store them in a local Chroma database."""
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=DB_DIR
    )
    vectorstore.persist()
    return vectorstore


def setup_qa_chain(vectorstore: Chroma, llm) -> RetrievalQA:
    """Set up the question-answering chain."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=retriever
    )
    return qa_chain


def main():
    llm = Ollama(model=LLM_MODEL)
    vectorstore = None
    last_check_time = 0

    while True:
        current_time = time.time()

        if current_time - last_check_time >= CHECK_INTERVAL:
            print("Checking for new documents...")
            result = load_and_process_documents(DOCUMENT_DIR)
            if result is not None:
                chunks, documents = result
                contextual_chunks = contextual_chunking(chunks, documents, llm)

                if vectorstore is None:
                    vectorstore = create_and_store_embeddings(contextual_chunks)
                else:
                    vectorstore.add_documents(contextual_chunks)
                    vectorstore.persist()

                last_check_time = current_time
                print("Document processing complete.")
            else:
                print("No documents found or error in processing.")

        if vectorstore is not None:
            qa_chain = setup_qa_chain(vectorstore, llm)

            question = input("Enter your question (or 'quit' to exit): ")
            if question.lower() == "quit":
                break

            answer = qa_chain.run(question)
            print(f"Answer: {answer}\n")
        else:
            print("Waiting for documents to be processed...")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
