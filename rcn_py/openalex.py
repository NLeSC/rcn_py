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



