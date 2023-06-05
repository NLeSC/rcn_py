import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import gensim
from gensim import corpora
from rcn_py import openalex

def build_corpus(publications, num_topics, max_ngram_length=2):
    # Download necessary NLTK resources
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

    # Initialize tokenizer, stopwords, and lemmatizer
    tokenizer = nltk.RegexpTokenizer(r'\w+')
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()

    # Extract title and abstract from each publication
    documents = []
    for publication in publications:
        title = publication['title']
        if publication['description']:
            abstract = publication['description']
            documents.append(title + ' ' + abstract)
        else:
            documents.append(title)

    # Tokenize, remove stopwords, and lemmatize documents
    tokenized_documents = []
   
    for document in documents:
        tokens = tokenizer.tokenize(document.lower())
        filtered_tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]
        tokenized_documents.append(' '.join(filtered_tokens))

    # Create TF-IDF matrix
    vectorizer = TfidfVectorizer(ngram_range=(1, max_ngram_length), min_df=5)
    tfidf_matrix = vectorizer.fit_transform(tokenized_documents)

    # Apply Latent Dirichlet Allocation (LDA) for topic modeling
    lda_model = LatentDirichletAllocation(n_components=num_topics, random_state=42)
    lda_matrix = lda_model.fit_transform(tfidf_matrix)

    # Assign the group number to each publication
    groups = []
    topics = []
    for i, publication in enumerate(publications):
        groups.append(lda_matrix[i].argmax())
    for topic_idx, topic in enumerate(lda_model.components_):
        top_words_indices = topic.argsort()[:-11:-1]
        top_words = [vectorizer.get_feature_names_out()[index] for index in top_words_indices if topic[index] > 0.01]
        topics.append(top_words)
        
    return groups,topics


def openalex_build_corpus(works):
    keywords_list = []
    for w in works:
        if (w['doi']):
            keywords = openalex.publication_keywords(w['doi'])
            keywords_list.append(keywords)
        else:
            continue

    dictionary = corpora.Dictionary(keywords_list)
    corpus = [dictionary.doc2bow(keywords) for keywords in keywords_list]

    # Train LDA Model
    num_topics = 10  # Specify the number of topics
    lda_model = gensim.models.LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=10)

    # Get Topics and Assign Topic Names
    topics = lda_model.print_topics(num_words=5)  # Specify the number of words per topic

    # Print and Save Topic Names
    topic_names = {}
    for i, publication in enumerate(works):
        publication_topics = lda_model.get_document_topics(corpus[i])
        top_topic = max(publication_topics, key=lambda x: x[1])[0]  # Get the topic with the highest weight for the publication
        top_keywords = [word.split("*")[1].strip().replace('"', '') for word in topics[top_topic][1].split("+")]
        # topic_names[i] = ", ".join(top_keywords)
        topic_names[i] = {"topic_name": ", ".join(top_keywords), "group_id": top_topic}
        publication["topic_name"] = top_keywords
        publication["group_id"] = top_topic

    # Return topic names for each publication
    return topic_names, works

