import re
import time
import numpy as np

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

import gensim
from gensim import corpora

from crossref.restful import Works

ps = PorterStemmer()

def clean_text(text):
    nltk.download("stopwords")
    # nltk.download("wordnet")
    stop_words = set(stopwords.words("english"))

    text = text.replace("\n", " ")
    text = re.sub(r"-", " ", text)
    text = re.sub(r"\d+/\d+/\d+", "", text)
    text = re.sub(r"[0-2]?[0-9]:[0-6][0-9]", "", text)
    text = re.sub(r"[\w]+@[\.\w]+", "", text)
    text = re.sub(
        r"/[a-zA-Z]*[:\//\]*[A-Za-z0-9\-_]+\.+[A-Za-z0-9\.\/%&=\?\-_]+/i", "", text
    )
    pure_text = ""
    for letter in text:
        # Leave only letters and spaces
        if letter.isalpha() or letter == " ":
            letter = letter.lower()
            pure_text += letter

    corpus_lst = [ps.stem(word) for word in pure_text.split() if word not in stop_words]
    return corpus_lst

# LDA model for Scopus and RSD data (title + description)
def lda_cluster_description(docs):
    cleaned_abs_corpus = []
    for i in range(len(docs)):
        if docs.description[i]:
            cleaned_abs_corpus.append(clean_text(docs.description[i]))
        else:
            cleaned_abs_corpus.append(clean_text(docs.title[i]))

    num_topics = 4
    dictionary = corpora.Dictionary(cleaned_abs_corpus)
    corpus = [dictionary.doc2bow(text) for text in cleaned_abs_corpus]

    time.time()
    passes = 150
    np.random.seed(1)

    lda_model = gensim.models.LdaMulticore(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        chunksize=4000,
        batch=True,
        minimum_probability=0.001,
        iterations=350,
        passes=passes,
    )
    group = []
    for i in range(len(cleaned_abs_corpus)):
        scores = []
        for j1, j2 in lda_model[corpus[i]]:
            scores.append(j2)
        group.append(scores.index(max(scores)))
    docs["group"] = group
    return docs

def lemmatize_stemming(text):
    return ps.stem(WordNetLemmatizer().lemmatize(text, pos="v"))


# Tokenize and lemmatize
def preprocess(text):
    result = []
    for token in gensim.utils.simple_preprocess(text):
        if token not in gensim.parsing.preprocessing.STOPWORDS and len(token) > 3:
            result.append(lemmatize_stemming(token))

    return result


def orcid_lda_cluster(dois):
    cleaned_abs_corpus = []
    clusters = {}
    works = Works()
    for i in dois:
        w = works.doi(i)
        if "abstract" in w.keys():
            cleaned_abs_corpus.append(preprocess(w["abstract"]))
        elif "title" in w.keys() and w["title"]:
            cleaned_abs_corpus.append(preprocess(w["title"][0]))
        else:
            cleaned_abs_corpus.append([])

    dictionary = gensim.corpora.Dictionary(cleaned_abs_corpus)
    corpus = [dictionary.doc2bow(text) for text in cleaned_abs_corpus]

    lda_model = gensim.models.LdaMulticore(
        corpus, num_topics=8, id2word=dictionary, passes=10, workers=2
    )

    idx2topics = {}
    for idx, topic in lda_model.print_topics(-1):
        idx2topics[idx] = topic

    for i in range(len(cleaned_abs_corpus)):
        scores = []
        topics = []
        for j1, j2 in lda_model[corpus[i]]:
            topics.append(j1)
            scores.append(j2)
            clusters[dois[i]] = scores.index(max(scores))

    return clusters, idx2topics


# ############################## OpenAlex ################################
# LDA model for OpenAlex (which has concept info)
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


def openalex_build_corpus(works, num_topics):
    keywords_list = []
    for w in works:
        concepts = w['concepts']
        keywords = []
        if concepts:   
            for n in concepts[:10]:
                keywords.append(n["display_name"])
        else:
            keywords.append("")
        keywords_list.append(keywords)
        

    dictionary = corpora.Dictionary(keywords_list)
    corpus = [dictionary.doc2bow(keywords) for keywords in keywords_list]

    # Train LDA Model
    # num_topics = 10  # Specify the number of topics
    lda_model = gensim.models.LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=10)

    # Get Topics and Assign Topic Names
    topics = lda_model.print_topics(num_words=5)  # Specify the number of words per topic

    topic_lists = []
    for t in topics:
        top_keywords = [word.split("*")[1].strip().replace('"', '') for word in t[1].split("+")]
        topic_lists.append(top_keywords)

    # Count the frequency of each word
    word_counts = {}
    for topic in topic_lists:
        for word in topic:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Remove words that appear in more than half of the lists
    filtered_topics = []
    threshold = len(topic_lists) / 2
    for topic in topic_lists:
        filtered_topic = [word for word in topic if word_counts[word] <= threshold]
        filtered_topics.append(filtered_topic)

    # Print and Save Topic Names
    topic_names = {}
    for i, publication in enumerate(works):
            publication_topics = lda_model.get_document_topics(corpus[i])
            top_topic = max(publication_topics, key=lambda x: x[1])[0]  # Get the topic with the highest weight for the publication
            top_keywords = filtered_topics[top_topic]
            topic_names[top_topic] = ", ".join(top_keywords)
            # topic_names[i] = {"topic_name": ", ".join(top_keywords), "group_id": top_topic}
            
            publication["topic_name"] = top_keywords
            publication["group_id"] = top_topic
    # Return topic names for each publication
    return topic_names, works

