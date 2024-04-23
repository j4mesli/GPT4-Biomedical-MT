
import os
import sys
import random
import nltk

from langdetect import detect

from Bio import Entrez
Entrez.email = "EMAIL"

# pubmed

line_counts = {}

def get_set_articles(records):
	return records["PubmedArticle"]

def get_pmid(record):
	return record["MedlineCitation"]["PMID"]

def get_abstract_text(record):
	all_abstracttexts = []
	try:
		texts = []
		texts.append(record["MedlineCitation"]["Article"]['Abstract']['AbstractText'])
		if 'OtherAbstract' in record["MedlineCitation"]:
			for item in record["MedlineCitation"]['OtherAbstract']:
				texts.append(item['AbstractText'])
		abstracttext = ""
		for text in texts:
			if len(text)>1:
				abstracttext = ""
				for part in text:
					if len(part.attributes)>0:
						label = part.attributes['Label']
					else:
						label = 'None'
					part = part.replace('"', "'")
					abstracttext += part+" "
			else:
				abstracttext = text[0]
				abstracttext = abstracttext.replace('"',"'")
			all_abstracttexts.append(abstracttext.strip())
	except:
		print('PMID '+get_pmid(record)+' - abstract not found!')
	return all_abstracttexts

def build_article(record):
	articles = []	
	langs = []
	all_abstracttexts = get_abstract_text(record)
	for index in range(0,len(all_abstracttexts)):
		article = {}
		article["pmid"] = get_pmid(record)
		article["abstracttext"] = all_abstracttexts[index]
		# lang
		lang = detect(article["abstracttext"]) 
		article["lang"] = lang
		langs.append(lang)
		articles.append(article)
	return articles, langs

# fetch

def fetch_pubmed_articles(ids):
	ids = ",".join(ids)
	handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
	records = Entrez.read(handle)
	#print(records)
	set_articles = []
	set_langs = []
	for record in get_set_articles(records):
		#print(record)
		article, langs = build_article(record)
		set_articles.append(article)
		set_langs.append(langs)
	handle.close()
	#print(len(articles))
	return set_articles, set_langs

def fetch_multiple_articles(pmids, out_dir, lang1, lang2):
	processed_pmids_lang1 = set()
	processed_pmids_lang2 = set()
	set_articles, set_langs = fetch_pubmed_articles(pmids)
	for index in range(0,len(set_articles)):
		langs = set_langs[index]
		#print(langs)
		if len(langs)<2 or lang1 not in langs or lang2 not in langs:
			continue
		article = set_articles[index]
		for item in article:
			lang = detect(item["abstracttext"])
			if lang!=lang1 and lang!=lang2:
				continue
			processed_pmids = processed_pmids_lang1 if lang == lang1 else processed_pmids_lang2
			if item["pmid"] in processed_pmids:
				print(f'Duplicate PMID found for {lang}: {item["pmid"]}')
				continue	
			processed_pmids.add(item["pmid"])
			if lang not in line_counts:
				line_counts[lang] = 0
			if line_counts[lang] < 100:
				with open(os.path.join(out_dir, lang + ".txt"), "a") as writer:
					sentences = nltk.sent_tokenize(item["abstracttext"])
					random.seed(item["pmid"])
					while True:
						random_index = random.randint(0, len(sentences) - 1)
						line = sentences[random_index].strip()
						if len(line) > 20 and not line[0].isdigit() and not line[0] in [".", ",", ";", ":", "!", "?"]:
							#print(line[0])
							break
					writer.write(item["pmid"] + '\t')
					writer.write(line + "\n")
					line_counts[lang] += 1
				writer.close()
			else:
				print('Reached 100 lines for ' + lang + '!')
				if all(count == 100 for count in line_counts.values()):
					print('All languages have reached 100 lines. Stopping program.')
					sys.exit(0)
				return  

map_langs = {
	"eng": "en",
	"ita": "it",
	"chi": "zh-cn",
	"fre": "fr",
	"ger": "de",
	"por": "pt",
	"spa": "es",
	"rus": "ru" 
}

def get_lang1_lang2(filename):
	lang1, lang2 = filename[8:15].split("_")
	lang1 = map_langs[lang1]
	lang2 = map_langs[lang2]
	return lang1, lang2

def retrieve_abstracts(file_path, out_dir):
	filename =  os.path.basename(file_path)
	lang1, lang2 = get_lang1_lang2(filename)
	pmids = []	
	with open(file_path, "r") as reader:
		lines = reader.readlines()
		for line in lines:
			pmid = line.strip()
			pmids.append(pmid)
			if len(pmids)<100:
				continue
			# fetch
			fetch_multiple_articles(pmids,out_dir,lang1,lang2)
			pmids = []
	if len(pmids)>0:
		fetch_multiple_articles(pmids, out_dir, lang1, lang2)

if __name__ == '__main__':
	retrieve_abstracts(sys.argv[1],sys.argv[2])
