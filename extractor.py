import speech_recognition as sr

from deepsegment import DeepSegment
import nltk
from rake_nltk import Rake

class Extractor:
  def __init__(self, min_words = 15, num_keywords = 10):
    self.__segmenter = DeepSegment("en")
    self.__rake = Rake(max_length = 1)
    self.__r = sr.Recognizer()
    self.__min_words = min_words
    self.__num_keywords = num_keywords
    nltk.download("stopwords")
  
  def extract(self, audio_path):
    with sr.AudioFile(audio_path) as source:
      audio = self.__r.record(source)
    transcript = self.__r.recognize_google(audio)
    sentences = self.__segmenter.segment_long(transcript)
    self.__rake.extract_keywords_from_text(transcript)
    keywords = self.__rake.get_ranked_phrases()[:self.__num_keywords]
    last_sentence = ""
    
    for sentence in reversed(sentences):
      if len(last_sentence) >= self.__min_words:
        break
      else:
        last_sentence = f"{sentence} {last_sentence}"
    
    return keywords, last_sentence

if __name__ == "__main__":
  # Min words in last sentence, number keywords
  extractor = Extractor(15, 10)
  keywords, last_sentence = extractor.extract("test/adam.flac")
  print(keywords)
  print(last_sentence)
