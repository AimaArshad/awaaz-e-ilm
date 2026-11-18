from rapidfuzz import fuzz

query = "photosynthesis"
sentence = "Today we discuss photosynthesis."

score = fuzz.token_set_ratio(query, sentence)
print(f"Score for '{query}' against '{sentence}': {score}")