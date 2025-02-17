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


class ContextualRAG:
    """
    A class to handle Contextual Retrieval Augmented Generation (RAG) tasks.

    This class encapsulates functionality for loading documents, processing them,
    creating embeddings, and setting up a question-answering system.
    """

    def __init__(
        self,
        document_dir: str = "RAG_document_store",
        db_dir: str = "vectorstore",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "llama3.1:latest",
        check_on_init: bool = False,
    ):
        """
        Initialize the ContextualRAG object.

        Args:
            document_dir (str): Directory containing the documents to process.
            db_dir (str): Directory to store the vector database.
            chunk_size (int): Size of text chunks for processing.
            chunk_overlap (int): Overlap between text chunks.
            embedding_model (str): Name of the embedding model to use.
            llm_model (str): Name of the language model to use.
            check_on_init (bool): Whether to check and process documents during initialization.
        """
        self.document_dir = document_dir
        self.db_dir = db_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.llm_model = llm_model

        self.llm = Ollama(model=self.llm_model)
        self.embeddings = OllamaEmbeddings(model=self.embedding_model)
        self.vectorstore = self._initialize_vectorstore()

        if check_on_init:
            print("Checking for documents during initialization...")
            self.process_documents()

    def _initialize_vectorstore(self) -> Optional[Chroma]:
        """Initialize the vector store if it exists."""
        if os.path.exists(self.db_dir):
            try:
                return Chroma(
                    persist_directory=self.db_dir, embedding_function=self.embeddings
                )
            except ImportError:
                print("Error initializing vector store.")
                return None
        return None

    @staticmethod
    def get_document_hash(content: str) -> str:
        """Generate a hash for the document content to check for duplicates."""
        return hashlib.md5(content.encode()).hexdigest()

    def unified_document_loader(self, file_path: str) -> List[Document]:
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
        self,
    ) -> Optional[Tuple[List[Document], List[Document]]]:
        """Load documents from the directory and process them."""
        documents = []

        # Walk through the directory to find files
        for root, _, files in os.walk(self.document_dir):
            for file in files:
                file_path = os.path.join(root, file)
                loaded_docs = self.unified_document_loader(file_path)

                for doc in loaded_docs:
                    content = doc.page_content
                    content_hash = self.get_document_hash(content)

                    # Check if the document already exists in the vectorstore
                    if self.vectorstore:
                        existing_docs = self.vectorstore.get(
                            where={"source": file_path}
                        )
                        print(
                            f"Checking for existing documents for {file_path}: Found {len(existing_docs)} document(s)."
                        )

                        if (
                            isinstance(existing_docs, dict)
                            and "metadatas" in existing_docs
                        ):
                            found_existing = False

                            for metadata in existing_docs["metadatas"]:
                                existing_hash = metadata.get("content_hash")
                                print(
                                    f"Comparing hashes: Existing Hash: {existing_hash}, New Hash: {content_hash}"
                                )

                                if existing_hash == content_hash:
                                    print(
                                        f"Skipping {file_path} as it's already in the database."
                                    )
                                    found_existing = True
                                    break

                            if found_existing:
                                continue
                        else:
                            print(
                                f"No matching document found for {file_path}. Adding as new."
                            )

                    # Add metadata and append document
                    doc.metadata["content_hash"] = content_hash
                    doc.metadata["source"] = file_path
                    documents.append(doc)

        if not documents:
            print(f"No new or modified documents found in {self.document_dir}.")
            return [], []

        # Split documents into chunks for processing
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

        chunks = text_splitter.split_documents(documents)
        return chunks, documents

    def contextual_chunking(
        self, chunks: List[Document], documents: List[Document]
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
            full_doc = next(
                (
                    doc.page_content
                    for doc in documents
                    if doc.metadata["source"] == chunk.metadata["source"]
                ),
                "",
            )

            context = self.llm.invoke(
                prompt.format(full_doc=full_doc, chunk=chunk.page_content)
            )
            contextual_chunks.append(
                Document(
                    page_content=f"Context: {context}\n\nChunk: {chunk.page_content}",
                    metadata=chunk.metadata,
                )
            )

        return contextual_chunks

    def create_and_store_embeddings(self, chunks: List[Document]) -> None:
        """Create embeddings and store them in a local Chroma database."""
        if self.vectorstore is None:
            self.vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_dir,
            )
        else:
            self.vectorstore.add_documents(chunks)

    def setup_qa_chain(self) -> RetrievalQA:
        """Set up the question-answering chain."""
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        return RetrievalQA.from_chain_type(
            llm=self.llm, chain_type="stuff", retriever=retriever
        )

    def process_documents(self) -> None:
        """Process documents and update the vector store."""
        result = self.load_and_process_documents()

        if result is not None:
            chunks, documents = result

            if not chunks:
                print("No new chunks generated from documents.")
                return

            contextual_chunks = self.contextual_chunking(chunks, documents)

            if not contextual_chunks:
                print("No contextual chunks to add to the vector store.")
                return

            try:
                self.create_and_store_embeddings(contextual_chunks)
                print("Document processing complete.")
            except Exception as e:
                print(f"Error adding documents to vectorstore: {e}")

    def run(self) -> None:
        """Main method to run the ContextualRAG system."""
        if self.vectorstore is None:
            print(
                "No documents have been processed. Please initialize with check_on_init=True or call process_documents() manually."
            )
            return

        while True:
            qa_chain = self.setup_qa_chain()

            question = input("Enter your question (or 'quit' to exit): ")
            if question.lower() == "quit":
                break

            answer = qa_chain.run(question)
            print(f"Answer: {answer}\n")


if __name__ == "__main__":
    # Initialize the ContextualRAG system with document checking on initialization
    rag_system = ContextualRAG(check_on_init=True)
    rag_system.run()
