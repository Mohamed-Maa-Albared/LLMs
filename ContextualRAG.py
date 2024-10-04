import hashlib
import os
import time
from typing import List, Optional, Tuple

from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    CSVLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama

# Configuration
DOCUMENT_DIR = "documents"
DB_DIR = "vectorstore"
CHECK_INTERVAL = 600  # seconds
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.1:latest"


def get_document_hash(content: str) -> str:
    """Generate a hash for the document content to check for duplicates."""
    return hashlib.md5(content.encode()).hexdigest()


def unified_document_loader(file_path: str) -> List[Document]:
    """Load documents of various formats based on file extension."""
    _, file_extension = os.path.splitext(file_path)
    try:
        if file_extension.lower() == ".txt":
            return TextLoader(file_path).load()
        elif file_extension.lower() == ".csv":
            return CSVLoader(file_path).load()
        elif file_extension.lower() == ".pdf":
            return PyPDFLoader(file_path).load()
        elif file_extension.lower() in [".doc", ".docx"]:
            return UnstructuredWordDocumentLoader(file_path).load()
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")
        return []


def load_and_process_documents(
    directory: str, vectorstore: Optional[Chroma] = None
) -> Optional[Tuple[List[Document], List[Document]]]:
    """Load documents from a directory and process them."""
    documents = []

    # Walk through the directory to find files
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            loaded_docs = unified_document_loader(file_path)

            for doc in loaded_docs:
                content = doc.page_content
                content_hash = get_document_hash(content)

                # Check if the document already exists in the vectorstore
                if vectorstore:
                    existing_docs = vectorstore.get(where={"source": file_path})
                    print(
                        f"Checking for existing documents for {file_path}: Found {len(existing_docs)} document(s)."
                    )
                    # Ensure existing_docs is a list and not empty before accessing it
                    if isinstance(existing_docs, dict) and "metadatas" in existing_docs:
                        found_existing = (
                            False  # Flag to check if we found a matching document
                        )

                        # Iterate through all existing metadatas to find a match
                        for metadata in existing_docs["metadatas"]:
                            existing_hash = metadata.get("content_hash")

                            # Log both hashes for debugging
                            print(
                                f"Comparing hashes: Existing Hash: {existing_hash}, New Hash: {content_hash}"
                            )

                            # Compare hashes to decide whether to skip or add the document
                            if existing_hash == content_hash:
                                print(
                                    f"Skipping {file_path} as it's already in the database."
                                )
                                found_existing = True
                                break  # Exit loop since we found a match

                        if found_existing:
                            continue  # Skip adding this document
                    else:
                        print(
                            f"No matching document found for {file_path}. Adding as new."
                        )

                # Add metadata and append document
                doc.metadata["content_hash"] = content_hash
                doc.metadata["source"] = file_path
                documents.append(doc)

    # Check if any new or modified documents were found
    if not documents:
        print(f"No new or modified documents found in {directory}.")
        return [], []  # Return empty lists instead of None

    # Split documents into chunks for processing
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

    # Create a Chroma vector store from the document chunks
    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=DB_DIR
    )

    # Persist the vector store to disk
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

    # Initialize vectorstore if it exists
    if os.path.exists(DB_DIR):
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        try:
            vectorstore = Chroma(
                persist_directory=DB_DIR, embedding_function=embeddings
            )
        except ImportError:
            return
    else:
        vectorstore = None

    last_check_time = 0

    while True:
        current_time = time.time()

        if current_time - last_check_time >= CHECK_INTERVAL:
            print("Checking for new or modified documents...")
            result = load_and_process_documents(DOCUMENT_DIR, vectorstore)

            if result is not None:
                chunks, documents = result

                # Check if chunks are empty before processing
                if not chunks:
                    print("No new chunks generated from documents.")
                    last_check_time = (
                        current_time  # Update time to avoid immediate re-check
                    )
                    continue  # Skip to the next iteration

                contextual_chunks = contextual_chunking(chunks, documents, llm)

                # Check if contextual_chunks is empty before adding to vectorstore
                if not contextual_chunks:
                    print("No contextual chunks to add to the vector store.")
                    last_check_time = (
                        current_time  # Update time to avoid immediate re-check
                    )
                    continue  # Skip to the next iteration

                if vectorstore is None:
                    vectorstore = create_and_store_embeddings(contextual_chunks)
                else:
                    try:
                        vectorstore.add_documents(contextual_chunks)
                        vectorstore.persist()
                    except Exception as e:
                        print(f"Error adding documents to vectorstore: {e}")

                last_check_time = current_time
                print("Document processing complete.")
            else:
                print("No new or modified documents found.")

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
