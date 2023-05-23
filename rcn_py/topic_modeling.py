import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

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
