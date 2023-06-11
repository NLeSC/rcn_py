import requests
import orcid
import itertools

def search_user_by_orcid(orcid):
    url = "https://api.openalex.org/authors/https://orcid.org/"+orcid
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_search = resp.json()
    return openalex_search

def search_user_by_name(name):
    possible_orcid = orcid.name_to_orcid_id(name)
    result =search_user_by_orcid(possible_orcid)
    return result


def search_works_by_orcid(orcid):
    user_result = search_user_by_orcid(orcid)
    url = user_result['works_api_url']
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_search = resp.json()
    return openalex_search


def search_works_by_name(name):
    possible_orcid = orcid.name_to_orcid_id(name)
    result = search_works_by_orcid(possible_orcid)
    return result

def get_pub_info_by_doi(doi):
    url = "https://api.openalex.org/works?filter=doi:"+doi
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_pub_search = resp.json()
    return openalex_pub_search

def find_institution(institution_name):
    url = "https://api.openalex.org/institutions?search="+institution_name
    header = {'Accept' : 'application/json'}
    resp = requests.get(url, headers=header)
    openalex_aff_search = resp.json()
    return openalex_aff_search

def get_some_works_of_one_institution(institution_name):
    aff_results = find_institution(institution_name)['results']
    works_url = aff_results[0]['works_api_url']
    header = {'Accept' : 'application/json'}
    resp = requests.get(works_url, headers=header)
    work_search_per_page = resp.json()
            
    return work_search_per_page['results']

def get_works_of_one_institution(institution_name, work_count):
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
            # total_results = work_search_per_page['meta']['count']
            current_page = work_search_per_page['meta']['page']
            results_per_page = work_search_per_page['meta']['per_page']

            total_pages = (work_count + results_per_page - 1) // results_per_page
            if current_page == total_pages:
                break  # Break the loop when all pages have been retrieved

            params['page'] += 1 

    return openalex_aff_search

def get_all_works_of_one_institution(institution_name):
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

# Get all the coauthor institution information list for every work of one institution that we search for
def coauthor_institutions(institution_name):
    all_works = get_all_works_of_one_institution(institution_name)
    
    all_institution_info_list = []
    for work in all_works:
        current_work_inst_list = []
        for au in work['authorships']:
            for inst in au['institutions']:
                if inst['id'] and  inst not in current_work_inst_list:
                    current_work_inst_list.append(inst)
        all_institution_info_list.append(current_work_inst_list)

    return all_institution_info_list
                        

# Return nodes and links of institution coauthor networks 
# Nodes are institutions, and links are between institutions.
def build_institution_network(institution_name):
    all_works = get_all_works_of_one_institution(institution_name)

    node_id = 0 # node_id is from 0
    node_list = [] # Node info (no duplication)
    all_inst_id_list = [] # Used to check whether the institution has been saved
    coauthor_pair = []
    for work in all_works:
        current_work_inst_id_list = []
        for au in work['authorships']:
            for inst in au['institutions']:
                if inst['id']:
                    inst['openalex_id'] = inst['id']
                    if inst['openalex_id'] in all_inst_id_list:
                        existing_index = all_inst_id_list.index(inst['openalex_id'])
                        # Get the exsiting node id 
                        if existing_index not in current_work_inst_id_list:
                            current_work_inst_id_list.append(existing_index)
                    else:
                        inst['id'] = node_id
                        node_list.append(inst)
                        all_inst_id_list.append(inst['openalex_id'])
                        current_work_inst_id_list.append(node_id)
                        
                        node_id += 1
        coauthor_pair = coauthor_pair+list(itertools.combinations(current_work_inst_id_list, 2))

        # current_work_inst_id_list
    return node_list, coauthor_pair

            
    
def publication_keywords(doi):
    pub_info = get_pub_info_by_doi(doi)
    corpus = []
    concepts = pub_info["results"][0]["concepts"]
    if concepts:
        for n in concepts[:10]:
            corpus.append(n["display_name"])
    else:
        corpus.append("")
    return corpus
