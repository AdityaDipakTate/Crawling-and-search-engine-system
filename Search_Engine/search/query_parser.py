# lowercase
# remove punctuation
# tokenize
# remove stopwords
# stemming (optional initially)

import spacy

# Load the small English NLP model
nlp = spacy.load("en_core_web_sm")

# query = "The text miners are searching for the best hidden patterns in data."
query = input("Enter your search query: ")

# Process the sentence
doc = nlp(query)

# Extract lemmas for each token
lemmatized_words = [token.lemma_ for token in doc]

# Rejoin into a clean query string
lemmatized_query = " ".join(lemmatized_words)

print("Original query:", query)
print("Lemmatized query:", lemmatized_query)

# tokenize 
# stemming