import json
import boto3
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import OpenSearchVectorSearch
from langchain.prompts import PromptTemplate
from langchain.llms import Bedrock
from langchain.chains import RetrievalQA
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from requests_aws4auth import AWS4Auth
import time
import logging
import re
import os
from dotenv import load_dotenv
from langchain.llms import OpenAI

load_dotenv()

aoss_endpoint = os.environ.get("AOSS_ENDPOINT", "default_endpoint")
openai_api_key= os.environ.get("OPENAI_API_KEY", "default_api_key")
date = time.strftime("%Y-%m-%d %H:%M:%S")
dynamodb_client = boto3.resource('dynamodb')  
table = dynamodb_client.Table('maintenance-rag-bot')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        question = body['question']
    except:
        question = event['question']
    if not question:
        return {
            'statusCode': 400,
            'body': json.dumps('No question provided')
        }
    region = 'us-east-1'
    service = 'aoss'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    bedrock_client = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
    bedrock_embedder = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_client)
    index_name = 'rag-maintenance-doc'

    docsearch = OpenSearchVectorSearch(
        index_name=index_name,
        embedding_function=bedrock_embedder,
        opensearch_url=f'https://{aoss_endpoint}:443',
        http_auth=awsauth,
        is_aoss=True,
        timeout = 60,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection)

    retrieved_docs = docsearch.similarity_search_with_score(question, k=5)
    document_list = [item[0] for item in retrieved_docs]
    document_list = document_list[1:]
    retrieved_docs_context = '---\n'.join(f"{doc[0].page_content}\nSource: {(doc[0].metadata)}" for doc in retrieved_docs)
    
    extracted_data = []
    for doc in document_list:
        title = doc.metadata.get('title', 'N/A')
        extracted_data.append(title)
        answer_aditionaldata = extracted_data
    
    prompt_template = """
    Como asistente experto, mis respuestas se basan únicamente en los documentos recuperados de nuestra base de datos de proyectos. Proporcionaré una respuesta detallada y profunda a la pregunta utilizando estos documentos como contexto. También citaré todos los documentos fuentes proporcionando el documento del título que respalda mi respuesta.
    Este es el formato que seguiré:
    Respuesta: [Mi respuesta basada en el contexto]
    Documento de referencia: titulo del documento
    Pregunta: {question}
    Contexto: {context}
    """

    retriever = docsearch.as_retriever(search_kwargs={"k": 5})
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    llm = Bedrock(model_id="anthropic.claude-v2:1", client=bedrock_client, model_kwargs={'max_tokens_to_sample': 180000, 'temperature': 0.3, 'stop_sequences': ['Human:']})
    gpt = OpenAI(temperature=0.3, model_name='text-davinci-003',max_tokens=3000)
    try:
        chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, chain_type_kwargs={"prompt": prompt})
    except:
        chain = RetrievalQA.from_chain_type(llm=gpt, chain_type="stuff", retriever=retriever, chain_type_kwargs={"prompt": prompt})
    complete_query = f"Question: {question}\n\nContext:\n{retrieved_docs_context}"
    answer_llm = chain.run({"query": complete_query})
    table.put_item(Item={'date': date, 'question': question, 'answer': answer_llm})
    
    return {
        'statusCode': 200,
        'body': 
            {
                'answer':json.dumps(answer_llm),
                'source documents': json.dumps(answer_aditionaldata)
            }
        }