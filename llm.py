from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_history_aware_retriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate
from langchain import hub
import os
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from config import answer_example
store = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def get_retriever():
    embedding = OpenAIEmbeddings(model='text-embedding-3-large')
    index_name = 'datacenter-demo-index'
    database = PineconeVectorStore.from_existing_index(embedding=embedding, index_name=index_name)
    retriever = database.as_retriever(search_kwags={'k' : 4}) 
    return retriever


def get_llm(model='gpt-4o'):
    llm = ChatOpenAI(model='gpt-4o')    
    return llm


def get_dictionary_chain():
    llm = get_llm()
    dictionary = ["나광호 -> 장수혁"]
    prompt = ChatPromptTemplate.from_template(f"""
                                            사용자의 질문을 보고, 우리의 사전을 참고해서 사용자의 질문을 변경해주세요.
                                            만약 변경할 필요가 없다고 판단된다면, 사용자의 질문을 변경하지 않아도 됩니다.
                                            그런 경우에는 원래의 질문을 그대로 반환해주세요.
                                            사전: {dictionary}
                                            
                                            질문: {{question}}""")

    dictionary_chain = prompt | llm | StrOutputParser()

    return dictionary_chain


# def get_qa_chain():
#     llm = get_llm()
#     retriever = get_retriever()
#     LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
#     prompt = hub.pull("rlm/rag-prompt", api_key=LANGCHAIN_API_KEY)
#     qa_chain = RetrievalQA.from_chain_type(llm, retriever=retriever, chain_type_kwargs ={"prompt":prompt})

#     return qa_chain

def get_history_retriever():
    llm = get_llm()
    retriever = get_retriever()
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    prompt = hub.pull("rlm/rag-prompt", api_key=LANGCHAIN_API_KEY)

    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question"
        "which might reference context in the chat history, formulate a standalone question"
        "which can be understood without the chat history. Do NOT answer the question,"
        "just reformulate it if needed and otherwise return it as is."
    )


    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    return history_aware_retriever


def get_rag_chain():
    llm = get_llm()
    
    # This is a prompt template used to format each individual example.
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{answer}"),
        ]
    )
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=answer_example,
    )




    qa_system_prompt = (
        "당신은 데이터센터 전문가입니다. 사용자의 데이터센터에 관한 질문에 답변해주세요"
        "아래에 제공된 문서를 활용해서 답변해주시고"
        "답변을 알수 없다면 모른다고 답해주세요"
        "답변을 제공할 때는 우선 출처를 먼저 알려 주세요"
        "답변이 성공적이면 마지막에는 '감사합니다'를 붙여주세요"
        "답변이 실패적이면 마지막에는 '죄송합니다'를 붙여주세요"
        "\n\n"
        "{context}"
    )
    
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            few_shot_prompt,
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    
    history_aware_retriever = get_history_retriever()
    

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer"
    ).pick('answer')

    return conversational_rag_chain


def get_ai_response(user_message):

    dictionary_chain = get_dictionary_chain()
    rag_chain = get_rag_chain()
    datacenter_chain = {"input": dictionary_chain} | rag_chain
    ai_response = datacenter_chain.stream(
        {
            "question" : user_message
        },
        config={
            "configurable" : {"session_id":"123"}
        },
    )
    
    return ai_response

