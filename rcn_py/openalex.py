import sys
sys.path.append('./rcn_py')
import requests
import orcid
import itertools

def search_user_by_orcid(orcid):
    """
    This function takes an ORCID identifier as input,
    returns the author's profile information from OpenAlex API.
    """
    url = "https://api.openalex.org/authors/https://orcid.org/"+orcid
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_search = resp.json()
    return openalex_search

def search_user_by_name(name):
    """
    This function takes a person's name as input, 
    find an ORCID for that person using the orcid.name_to_orcid_id(name) function,
    then calls search_user_by_orcid(orcid) to fetch the author's profile information.
    """
    possible_orcid = orcid.name_to_orcid_id(name)
    result =search_user_by_orcid(possible_orcid)
    return result


def search_works_by_orcid(orcid):
    """
    This function takes an ORCID as input, fetches the author's profile, 
    then uses the 'works_api_url' from the author's profile to fetch all the works associated with that author.
    """
    user_result = search_user_by_orcid(orcid)
    url = user_result['works_api_url']
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_search = resp.json()
    return openalex_search


def search_works_by_name(name):
    """
    This function takes a person's name as input, 
    converts it to an ORCID, 
    and fetches all the works associated with that identifier.
    """
    possible_orcid = orcid.name_to_orcid_id(name)
    result = search_works_by_orcid(possible_orcid)
    return result

def get_pub_info_by_doi(doi):
    """
    This function takes a DOI as input 
    and uses it to fetch publication information from the OpenAlex API.
    """
    url = "https://api.openalex.org/works?filter=doi:"+doi
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_pub_search = resp.json()
    return openalex_pub_search

def find_institution(institution_name):
    """
    This function takes an institution name as input 
    and fetches the institution's profile from the OpenAlex API.
    """
    url = "https://api.openalex.org/institutions?search="+institution_name
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_aff_search = resp.json()
    return openalex_aff_search

def get_some_works_of_one_institution(institution_name):
    """
    This function takes an institution name as input 
    and fetches a list of works associated with that institution. 
    It only fetches the first page of results.
    """
    aff_results = find_institution(institution_name)['results']
    works_url = aff_results[0]['works_api_url']
    header = {'Accept' : 'application/json'}
    resp = requests.get(works_url, headers=header)
    work_search_per_page = resp.json()
            
    return work_search_per_page['results']

def get_works_of_one_institution(institution_name, work_count):
    """
    This function takes an institution name and a count of works as input, 
    fetches a list of works up to the specified count. 
    It fetches works in pages of 25 at a time until it reaches the specified count.
    """
    aff_results = find_institution(institution_name)['results']
    works_url = aff_results[0]['works_api_url']
    header = {'Accept' : 'application/json'}

    params = {
            'per_page': 25,  # Number of results per page
            'page': 1       # Initial page number
        }
    openalex_aff_search = []

    while True:
            resp = requests.get(works_url, headers=header, params=params)
            work_search_per_page = resp.json()
            openalex_aff_search.extend(work_search_per_page['results'])
            current_page = work_search_per_page['meta']['page']
            results_per_page = work_search_per_page['meta']['per_page']

            total_pages = (work_count + results_per_page - 1) // results_per_page
            if current_page == total_pages:
                break  # Break the loop when all pages have been retrieved

            params['page'] += 1 

    return openalex_aff_search

def get_all_works_of_one_institution(institution_name):
    """
    This function takes an institution name as input
    fetches all the works associated with that institution. 
    It fetches works in pages of 100 at a time until it has fetched all the works.
    """
    aff_results = find_institution(institution_name)['results']
    works_url = aff_results[0]['works_api_url']
    header = {'Accept' : 'application/json'}

    params = {
            'per_page': 100,  # Number of results per page
            'page': 1       # Initial page number
        }
    openalex_aff_search = []

    while True:
            resp = requests.get(works_url, headers=header, params=params)
            work_search_per_page = resp.json()
            openalex_aff_search.extend(work_search_per_page['results'])
            total_results = work_search_per_page['meta']['count']
            current_page = work_search_per_page['meta']['page']
            results_per_page = work_search_per_page['meta']['per_page']

            total_pages = (total_results + results_per_page - 1) // results_per_page
            if current_page == total_pages:
                break  # Break the loop when all pages have been retrieved

            params['page'] += 1 

    return openalex_aff_search

def get_works_of_one_institution_by_year(institution_name, start_year, end_year):
    """
    This function takes an institution name, a start year, and an end year as input, 
    and fetches all the works associated with that institution that were published between the specified years. 
    It fetches works in pages of 100 at a time until it has fetched all the works for the specified years.
    """
    aff_results = find_institution(institution_name)['results']
    works_url = aff_results[0]['works_api_url']

    api_url = works_url+',publication_year:' + start_year + '-' + end_year + '&sort=publication_date:desc'
    header = {'Accept' : 'application/json'}

    params = {
                'per_page': 100,  # Number of results per page
                'page': 1       # Initial page number
            }
    openalex_aff_search = []

    while True:
            resp = requests.get(api_url, headers=header, params=params)
            work_search_per_page = resp.json()
            openalex_aff_search.extend(work_search_per_page['results'])
            total_results = work_search_per_page['meta']['count']
            current_page = work_search_per_page['meta']['page']
            results_per_page = work_search_per_page['meta']['per_page']

            total_pages = (total_results + results_per_page - 1) // results_per_page
            if current_page == total_pages:
                break  # Break the loop when all pages have been retrieved

            params['page'] += 1 
    return openalex_aff_search


def coauthor_institutions(institution_name):
    # Call the get_all_works_of_one_institution function to fetch all works related to the given institution.
    all_works = get_all_works_of_one_institution(institution_name)
    
    # Initialize an empty list to store the information of all institutions for each work.
    all_institution_info_list = []
    # Loop through each work in the all_works list.
    for work in all_works:
        # Initialize an empty list to store the institutions for the current work.
        current_work_inst_list = []

        # For each authorship in the current work
        for au in work['authorships']:
            # And for each institution within that authorship
            for inst in au['institutions']:
                # If the institution has an 'id' and is not already in the current_work_inst_list
                if inst['id'] and  inst not in current_work_inst_list:
                    # Append the institution to the current_work_inst_list.
                    current_work_inst_list.append(inst)

        # After iterating through all authorships and their institutions, 
        # append the current_work_inst_list to the all_institution_info_list.
        all_institution_info_list.append(current_work_inst_list)

    return all_institution_info_list
                        

def build_institution_network(institution_name):
    # Get all works associated with the given institution
    all_works = get_all_works_of_one_institution(institution_name)

    node_id = 0 # node_id is from 0
    node_list = [] # Node info (no duplication)
    all_inst_id_list = [] # Used to check whether the institution has been saved
    coauthor_pair = [] # List to store pairs of coauthoring institutions

    for work in all_works:
        current_work_inst_id_list = [] # Track the institution IDs for the current work
        for au in work['authorships']:
            for inst in au['institutions']:
                if inst['id']:
                    inst['openalex_id'] = inst['id']
                    if inst['openalex_id'] in all_inst_id_list:
                        # The institution already exists, retrieve the existing node id
                        existing_index = all_inst_id_list.index(inst['openalex_id'])
                        # Add the existing node id to the current_work_inst_id_list
                        if existing_index not in current_work_inst_id_list:
                            current_work_inst_id_list.append(existing_index)
                    else:
                        # The institution is encountered for the first time, assign a new node id
                        inst['id'] = node_id
                        node_list.append(inst) # Add the institution to the node_list
                        # Add the institution id to all_inst_id_list for future reference
                        all_inst_id_list.append(inst['openalex_id']) 
                        # Add the new node id to the current_work_inst_id_list
                        current_work_inst_id_list.append(node_id)
                        
                        node_id += 1 # Increment the node_id for the next node

        # Generate coauthor pairs for the current work and add them to the coauthor_pair list
        coauthor_pair = coauthor_pair+list(itertools.combinations(current_work_inst_id_list, 2))

    return node_list, coauthor_pair

            
    
def publication_keywords(doi):
    # Retrieve publication information using DOI
    pub_info = get_pub_info_by_doi(doi)

    corpus = [] # List to store the keywords

    # Extract concepts from publication information
    concepts = pub_info["results"][0]["concepts"]
    if concepts:
        # If concepts exist, add the display names of the top 10 concepts to the corpus list
        for n in concepts[:10]:
            corpus.append(n["display_name"])
    else:
        # If no concepts are found, add an empty string to the corpus list
        corpus.append("")
        
    return corpus
