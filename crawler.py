import json
import urllib
import warnings

class SemanticScholarMetaDataExtractor():
    def __init__(self):
        self.API_ID = 'https://api.semanticscholar.org/v1/paper/arXiv:'

    def get_response(self, paper_id):
        paper_url = self.API_ID+paper_id
        return urllib.request.urlopen(paper_url)
    
    def get_data_json(self, paper_id):
        response = self.get_response(paper_id)
        return json.loads(response.read())

class ArXivPaper():
    def __init__(self, paper):
        self.paper = paper

        self.essential_metadata_keys = {'abstract', 'arxivId', 'authors', 'citations', 'influentialCitationCount',
                                        'doi', 'fieldsOfStudy', 'paperId', 'references',
                                        'title', 'topics', 'url', 'venue', 'year'}

        self.representational_info_keys = ['abstract', 'authors', 'url', 'year',
                                           'fieldsOfStudy', 'numCitations', 'venue', 'numReferences']
        
        self.check_paper()
        self.check_relevant_keys()
        self.discard_non_influential_citations()
        self.discard_non_influential_references()
        self.discard_none_arxiv_references()
        self.discard_none_arxiv_citations()
        self.set_num_references()
        self.set_num_citations()

    def check_paper(self):
        if isinstance(self.paper, str):
            warnings.warn("Paper not present in memory. Extracting Paper MetaData from Semantic Scholar!")
            metadata_extractor = SemanticScholarMetaDataExtractor()
            self.paper = metadata_extractor.get_data_json(self.paper)
        
        elif not isinstance(self.paper, dict):
            raise TypeError("Paper must be a Dict or an Arxiv Id")
    
    def check_relevant_keys(self):
        missing_keys = self.essential_metadata_keys.difference(self.paper.keys())
        if not missing_keys == set():
            error_message = "The following essential keys are missing from the paper: " + \
                            ", ".join(missing_keys)
            raise KeyError(error_message)
        

    def discard_non_influential_citations(self):
        self.paper['citations'] = list(filter(lambda i: i['isInfluential'] is True, self.paper['citations']))

    def discard_none_arxiv_references(self):
        self.paper['references'] = list(filter(lambda i: i['arxivId'] is not None, self.paper['references'])) 

    def discard_none_arxiv_citations(self):
        self.paper['citations'] = list(filter(lambda i: i['arxivId'] is not None, self.paper['citations']))

    def discard_non_influential_references(self):
        self.paper['references'] = list(filter(lambda i: i['isInfluential'] is True, self.paper['references'])) 

    def set_num_references(self):
        self.paper['numReferences'] = len(self.paper['references'])

    def set_num_citations(self):
        self.paper['numCitations'] = len(self.paper['citations'])

    def __getitem__(self, key):
        return self.paper[key]
    
    def __repr__(self):
        repr = f"Paper Title: {self.__getitem__('title')} \n\n"
        for idx, key in enumerate(self.representational_info_keys):
            if key == 'abstract':
                repr += f"{idx+1}) {'Abstract'}: \n{self.__getitem__(key)} \n\n"
                continue
            if key == 'authors':
                repr += f"{idx+1}) {'Authors'}:\n"
                authors = self.__getitem__(key)
                for i, author in enumerate(authors):
                    repr += f"\t{i+1}) {'Name'}: {author.__getitem__('name')}\n"
                    repr += f"\t{'URL'}: {author.__getitem__('url')}\n"
                    repr +="\n"
                continue
            repr += f"{idx+1}) {key}: {self.__getitem__(key)} \n\n"
        return(repr)
    
    def get_top_k_citations_information(self, k:int):
        if k > self.__getitem__('numCitations'):
             warnings.warn(f"Total citations are {self.__getitem__('numCitations')}. Retrieving all citations")
             k = self.__getitem__('numCitations')

        citations = []
        all_citations = self.__getitem__('citations')

        info_keys = ['arxivId', 'authors', 'title', 'url','venue', 'year']

        i=0
        while i < k:
            citation = all_citations[i]        
            citation = {key:val for key, val in citation.items() if key in info_keys}
            citations.append(citation)
            i+=1

        return citations

    def get_top_k_references_information(self, k:int):
        if k > self.__getitem__('numReferences'):
             warnings.warn(f"Total references are {self.__getitem__('numReferences')}. Retrieving all references")
             k = self.__getitem__('numReferences')

        references = []
        all_references = self.__getitem__('references')

        info_keys = ['arxivId', 'authors', 'title', 'url','venue', 'year']

        i=0
        while i < k:
            reference = all_references[i]
            reference = {key:val for key, val in reference.items() if key in info_keys}
            references.append(reference)
            i+=1

        return references

    def get_top_k_references_metadata(self, k:int):
        reference_papers = []
        references = self.get_top_k_references_information(k)

        for i in range(len(references)):
            reference_papers.append(ArXivPaper(references[i]['arxivId']))

        return reference_papers

    def get_top_k_citations_metadata(self, k:int):
        citation_papers = []
        citations = self.get_top_k_citations_information(k)

        for i in range(len(citations)):
            citation_papers.append(ArXivPaper(citations[i]['arxivId']))

        return citation_papers
    

class GraphNode():
    def __init__(self, paper:ArXivPaper, num_citations:int=1, num_references:int=1):
        self.paper = paper 
        self.num_citations = num_citations
        self.num_references = num_references
        self.citation_children = None
        self.reference_children = None
    
    def is_reference_leaf(self):
         return self.paper['numReferences'] == 0

    def is_citation_leaf(self):
         return self.paper['numCitations'] == 0
    
    def get_citation_children(self):
        if not self.is_citation_leaf():
            self.citation_children = self.paper.get_top_k_citations_information(self.num_citations)

    def get_reference_children(self):
        if not self.is_reference_leaf():
            self.reference_children = self.paper.get_top_k_references_information(self.num_references)

    def get_citation_children_metadata(self):
        essential_metadata_keys = ['abstract', 'arxivId', 'numCitations', 'title']
        citation_children_metadata = self.paper.get_top_k_citations_metadata(self.num_citations)
        
        for idx, child in enumerate(citation_children_metadata):
            citation_children_metadata[idx] = {key:val for key, val in child.paper.items() if key in essential_metadata_keys}
        
        return citation_children_metadata

    def get_reference_children_metadata(self):
        essential_metadata_keys = ['abstract', 'arxivId', 'numReferences', 'title']
        reference_children_metadata = self.paper.get_top_k_references_metadata(self.num_references)

        for idx, child in enumerate(reference_children_metadata):
            reference_children_metadata[idx] = {key:val for key, val in child.paper.items() if key in essential_metadata_keys}

        return reference_children_metadata
