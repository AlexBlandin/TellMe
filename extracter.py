import speech_recognition as sr

from deepsegment import DeepSegment
import nltk
from rake_nltk import Rake

class Extracter:
	def __init__(self, min_words, num_keywords):
		self.__segmenter = DeepSegment('en')
		self.__rake = Rake(max_length=1)
		self.__r = sr.Recognizer()
		self.__min_words = min_words
		self.__num_keywords = num_keywords
		nltk.download('stopwords')
		
	def extract(self, audio_path):
		with sr.AudioFile(audio_path) as source:
			audio = self.__r.record(source)
		transcript = self.__r.recognize_google(audio)
		sentences = self.__segmenter.segment_long(transcript)
		self.__rake.extract_keywords_from_text(transcript)
		keywords = self.__rake.get_ranked_phrases()[:10]
		last_sentence = ''
		
		for sentence in reversed(sentences):
			if len(last_sentence) > self.__min_words:
				break
			else:
				last_sentence = sentence + ' ' + last_sentence
				
		
		return keywords, last_sentence
		
if __name__ == "__main__":
	# Min words in last sentence, number keywords
	extracter = Extracter(15,10)
	keywords, last_sentence = extracter.extract('test/adam.flac')
	print(keywords)
	print(last_sentence)
