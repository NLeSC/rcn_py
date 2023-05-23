import requests
import orcid

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
