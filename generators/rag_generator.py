"""
RAG Generator Module

This module provides test case generation using Retrieval-Augmented Generation (RAG).
It uses vector stores (FAISS) to retrieve relevant code context for better generation.
"""

import os
import json
import re
from typing import Optional, Dict, Any

try:
    import langchain
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains import create_retrieval_chain
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain.vectorstores import FAISS
except ImportError:
    langchain = None
    create_stuff_documents_chain = None
    create_retrieval_chain = None
    PromptTemplate = None
    Document = None
    RecursiveCharacterTextSplitter = None
    OpenAIEmbeddings = None
    ChatOpenAI = None
    FAISS = None

from config.constants import (
    ENV_OPENAI_API_KEY,
    DEFAULT_GPT_MODEL,
    DEFAULT_VECTORSTORE_PATH
)


def setup_rag_pipeline(
    lua_folder: str,
    vectorstore_path: str = DEFAULT_VECTORSTORE_PATH,
    model_name: str = DEFAULT_GPT_MODEL,
    temperature: float = 0
) -> list:
    """
    Set up a RAG pipeline for code retrieval and generation.
    
    Args:
        lua_folder: Path to folder containing Lua source code files
        vectorstore_path: Path to save/load FAISS vector store
        model_name: LLM model name for generation
        temperature: Temperature parameter for LLM
        
    Returns:
        List containing [retriever, prompt_template, llm]
        
    Raises:
        ImportError: If langchain packages are not installed
    """
    if langchain is None:
        raise ImportError("langchain packages required. Install with: pip install langchain langchain-openai faiss-cpu")
    
    # Load or create vector store
    if os.path.exists(vectorstore_path):
        vectorstore = FAISS.load_local(
            vectorstore_path,
            OpenAIEmbeddings(model='text-embedding-3-large'),
            allow_dangerous_deserialization=True
        )
    else:
        # Create vector store from Lua files
        def load_documents_with_metadata(base_folder: str, file_extension: str, is_lua: bool = False):
            documents = []
            for root, _, files in os.walk(base_folder):
                for file_name in files:
                    if file_name.endswith(file_extension):
                        file_path = os.path.join(root, file_name)
                        relative_path = os.path.relpath(file_path, base_folder)
                        metadata = {"source": relative_path}
                        
                        if is_lua:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            documents.append(Document(page_content=content, metadata=metadata))
                        else:
                            from langchain_community.document_loaders import UnstructuredFileLoader
                            loader = UnstructuredFileLoader(file_path, metadata=metadata)
                            documents.extend(loader.load())
            
            if is_lua:
                lua_separators = [
                    "\nand", "\nbreak", "\ndo", "\nelse", "\nelseif", "\nend", "\nfalse", "\nfor", "\nfunction",
                    "\ngoto", "\nif", "\nin", "\nlocal", "\nnil", "\nnot", "\nor", "\nrepeat", "\nreturn", "\nthen",
                    "\ntrue", "\nuntil", "\nwhile", '\n\n', '\n'
                ]
                lua_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=2048,
                    chunk_overlap=256,
                    length_function=len,
                    separators=lua_separators,
                )
                split_docs = lua_splitter.split_documents(documents)
            else:
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                split_docs = text_splitter.split_documents(documents)
            return split_docs
        
        lua_docs = load_documents_with_metadata(lua_folder, ".lua", is_lua=True)
        embedding_model = OpenAIEmbeddings(model='text-embedding-3-large')
        vectorstore = FAISS.from_documents(lua_docs, embedding_model)
        vectorstore.save_local(vectorstore_path)
    
    # Create prompt template
    prompt_template = PromptTemplate(
        input_variables=["context"],
        template=(
            """
            ### Instruction ###
            You are a helpful Testing Assistant skilled in understanding related source code, 
            and generating fuzzing cases for software black-box testing according to the 
            fuzzing policies below.
            It is imperative that your responses be strictly based on the text provided. 
            
            ### Fuzzing Policies ###
            - Changing Argument Values:  
                -- if the valid argument value is in a range and will be check the datatype, 
                   provide both extreme values(such as min and max of the valid range) and 
                   random valid values. 
                -- if the valid argument value is a string-type, change the length trying to 
                   trigger buffer overflows. 
                -- provide empty values to strings to trigger uninitialized read or null 
                   pointer deference. 
                -- provide NULL or only one element to arrays, sets, or bags to cause null 
                   pointer deference or out-of-bounds access 
            - Changing Argument Types:  
                -- if there is no datatype check in the source code of a function, change the 
                   argument data type from t to a randomly selected one t', to check whether the 
                   program can handle the special type. 
            - Changing the Number of Arguments:  
                -- For a function requiring n arguments, mutate the cases providing n+1, n−1, 
                   or 0 arguments. 
            
            ### Chain of Thought ###
            1. According to the API specification given in the question, list the functions
               (both Static Methods and Methods);
            2. For each API function, according to the specification, extract the related 
               source code in Lua;
            3. For the source code of each API function, check the arguments and if there is 
               datatype checking, i.e. 'data_types.validate_or_build_type()' called;
            4. For each API function, generate three fuzzing cases for exploring vulnerabilities 
               purpose.
            
            ### Example of Fuzzing Test Cases ###
            You may list every fuzzing(test) case starting with 'Test_Case' followed by the 
            number of the current test case. The "API_Name" should converted, i.e. from 
            "st.zigbee.zdo.BindRequest" to "zdo/mgmt_bind_request". Here is an example of 
            generated fuzzing case:
            ```
            [
                {{
                    "Test_Case": 1,
                    "API_Name": "zdo/mgmt_bind_request",
                    "Function_Name": "from_values",
                    "Description": "Call from_values with appropriate values for start_index.",
                    "Code_Snippets": [
                        "MgmtBindRequest.from_values({{}}, 0)", 
                        "MgmtBindRequest.from_values({{}}, 1)",
                        "MgmtBindRequest.from_values({{}}, 2)"
                    ]
                }}
            ]
            ```
            
            Note:
            - Please avoiding mutating the parameter within a function, e.g. 
              ""Code_Snippets": ["deserialize(string.rep('A', 10^6))":", while you may note 
              the pre-operation needed to be executed in Python, e.g. 
              ""Pre-operation_Python": ["temp = 'A'*10^6"], "Code_Snippets": ["deserialize(temp)"]"
            - Please generating the fuzzing cases with code_snippets for calling existing 
              functions mentioned in the provided specification. Note that the fuzzing environment 
              disabled load() and loadfile() functions, so avoiding mutating any self-defined 
              functions.
            
            Use the following context of API source code in Lua to answer the question:
            ```{context}```
            """
        )
    )
    
    # Create LLM
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    
    return [vectorstore.as_retriever(), prompt_template, llm]


def generate_response(pipeline: list, query: str) -> Dict[str, Any]:
    """
    Generate a response using the RAG pipeline.
    
    Args:
        pipeline: RAG pipeline list [retriever, prompt_template, llm]
        query: Query/question to answer
        
    Returns:
        Response dictionary with answer and context
    """
    retriever = pipeline[0]
    prompt_template = pipeline[1]
    llm = pipeline[2]
    
    if langchain.__version__ > '0.3':
        question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
        retrieval_chain = create_retrieval_chain(retriever, question_answer_chain)
        return retrieval_chain.invoke({'input': query})
    else:
        from langchain.chains import RetrievalQA
        retrieval_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt_template},
        )
        return retrieval_chain.invoke({'query': query})


def extract_and_save_answer(
    data: Dict[str, Any],
    dest_dir: str,
    api: str,
    round_number: str
) -> None:
    """
    Extract JSON answer from RAG response and save to file.
    
    Args:
        data: Response data from RAG pipeline
        dest_dir: Destination directory
        api: API name
        round_number: Round number string
    """
    api_path = os.path.join(dest_dir, api)
    output_filename = os.path.join(api_path, f"cases-{round_number}.json")
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    raw_answer = data.get("answer", "")
    
    # Clean and parse JSON
    cleaned_answer = re.sub(r"```json\n|\n```", "", raw_answer).strip()
    
    try:
        answer_json = json.loads(cleaned_answer)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse 'answer' as JSON: {e}")
    
    with open(output_filename, "w", encoding="utf-8") as outfile:
        json.dump(answer_json, outfile, indent=4)
    
    print(f"Extracted 'answer' saved to: {output_filename}")

