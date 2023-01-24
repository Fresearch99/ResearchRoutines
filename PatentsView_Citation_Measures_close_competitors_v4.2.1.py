# -*- coding: utf-8 -*-
"""
Author: Dominik Jurek

DATE: 3/1/2021
METHOD: Construction skipt for several patent measures based on citations - Close Competitor Related
    VERSION 2: Construction of sparse matrix of patent citation on servers
    VERSION 3: Implement citation measures from Balsmeier, Fleming, Manso (2017)
        Subverison 3.1: Use IPC classification
        Subversion 3.2: Include construction of own measures of technogolocal proximity of Hoberg Philips Peers
        Subversion 3.3: Try to execute main only on demand
        Subversion 3.4: Memory Saving Chunking while loading large Patent Citation file
        Subversion 3.5: Parallel version of construction of own variables
        Subversion 3.6: Avoid global variable that would maximize communication between treads
    VERSION 4: Include filing date for citing patent & update KPPS data and for Google Cloud
        Subversion 4.1: Load relevant patent citations and classification data within annual peer
                    technological proximity method, to run as independent as possible from main
                    & Use map_async [based on PatentsView_Citation_Measures_close_competitors_v4.py]
        Subversion 4.2, close_competitors: Remove every BFM code elements that are not used to construct Close competitors
                        Explanation: Keeping global variables leads probably to memory excess that stops parallel exectution from working
                        & Include also apply_async method, since map_async might default to linear
            Subsubversion 4.2.1: Include itermediate saves to resume calculation after job reset
"""

# sbatch PatentsView_Citation_Measures_close_competitors_v4.2.sh
# seff JOB-ID for efficiency details

r'''
#!/bin/bash
#
# Submit this script using: sbatch script-name
#
#SBATCH -p c2s30 # partitions  c2-standard-30
#SBATCH -c 12 # number of cores
#SBATCH --mem 112G # memory pool for all cores
#SBATCH -o slurm.%N.%j.out # STDOUT
#SBATCH -e slurm.%N.%j.err # STDERR

cd $WORKING_DIR

srun ~/.conda/envs/py37/bin/python3 PatentsView_Citation_Measures_close_competitors_v4.2.py
r'''
# %%
#################################################################
# Load Packages
#################################################################

import pandas as pd
import numpy as np
import re
import os

import swifter

import requests
from io import BytesIO
from lxml import html

import zipfile
import csv

import multiprocessing as mp

import scipy.sparse
import pickle
from pandas.api.types import CategoricalDtype

import psutil
print('\t\t Memory usage: total {0:.2f} GB; available {1:.2f} GB;\n \
      \t\t free percent {2:2.1f}%; used {3:.2f} GB; free {4:.2f} GB'.format(
    psutil.virtual_memory()[0]/1024**3,
    psutil.virtual_memory()[1]/1024**3,
    psutil.virtual_memory()[2],
    psutil.virtual_memory()[3]/1024**3,
    psutil.virtual_memory()[4]/1024**3
    ), flush=True)

#---------------------------------------
# Define source directory for additional data to be loaded
source_directory = r'Patent_portfolio_structuring_source_directory'
#source_directory = r'C:\Users\domin\Google Drive\Preliminary Research\Alice and Innovation Project\Patent Portfolio and Economic Data\Patent_portfolio_structuring_source_directory'


# Directory for HP data
hp_directory = r'Hoberg_Phillips_data'

# Size of peer group to be measure constructed form
N_CLOSE_COMPETITORS = 20

#----------------------------------------
# Expand field limit to iterate through all claims
import ctypes
csv.field_size_limit(int(ctypes.c_ulong(-1).value // 2))
csv.field_size_limit()

#----------------------------------------
#Current Build
VERSION = 4

# Load variables version (note that the base Citation and Class data are constructed in PatentsView_Citation_Measures_vX)
LOAD_VERSION = 4

#----------------------------------------
# Define output path
OUTPUT_PATH = 'PatentsView_Citation_Measures_' + str(VERSION)

# File for patent scope measure
patent_scope_direcetory = 'KPSS_patent_abstract_claim_extraction_2.1/PatentsView_complete_data_first_claim_no_readability_2.1.csv'

#====================================
# Create Output Path if not already exist
if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)


pd.set_option('display.max_rows', 400)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 100)

# %%
##########################################################
# Citation based technology proximity measure            #
##########################################################

def _close_peer_construction():
    '''wrapper that generates tuple of permco1, year, and list of close peers'''
    #=======================================
    # Construct close peers group
    #=======================================

    # Load hoberg philips close peers
    tnic3hhi = pd.read_csv(hp_directory + '/tnic3_data.txt', delimiter="\t")

    # Exclude self references
    tnic3hhi = tnic3hhi[(tnic3hhi.gvkey1!=tnic3hhi.gvkey2)]

    # Limit to closes competitors
    tnic3hhi = tnic3hhi.sort_values('score', ascending=False).\
                        groupby(['gvkey1', 'year']).head(N_CLOSE_COMPETITORS).\
                            reset_index(drop=False).drop('index', axis=1)

    #-----------------------------------
    # Use linktable to link to permco
    #----------------------------------------------
    # Add gvkey identifier to Compustat data => use WRDS linktable from interface
    linktable = pd.read_csv(source_directory + '//linktable.csv', low_memory=False)
    #linktable = pd.read_csv(source_directory + '//crsp_ccm_link.csv')

    # Retrict to Primary on non-duplicate links (see https://wrds-www.wharton.upenn.edu/pages/support/applications/linking-databases/linking-crsp-and-compustat/)
    linktable = linktable[linktable.LINKTYPE.isin(['LU', 'LC']) & linktable.LINKPRIM.isin(['P', 'C'])]

    #linktable.LINKPRIM.value_counts()

    linktable = linktable[['gvkey', 'LPERMNO', 'LPERMCO', 'cusip',
                           'LINKDT', 'LINKENDDT', 'tic',
                           'conm', 'CONML', 'WEBURL']].drop_duplicates()

    # Change link end and start dates to date format
    linktable['linkdt'] = pd.to_datetime(linktable['LINKDT'], format='%Y%m%d', errors='coerce')
    linktable['linkenddt'] = pd.to_datetime(linktable['LINKENDDT'], format='%Y%m%d', errors='coerce')

    # if linkenddt is missing then set to first of 2020
    linktable['linkenddt'] = linktable['linkenddt'].fillna(pd.to_datetime('20211001', format='%Y%m%d'))

    # define permco and permno as string
    linktable['permno'] = pd.to_numeric(linktable['LPERMNO'],
                                        downcast = 'integer', errors = 'coerce')
    linktable['permco'] = pd.to_numeric(linktable['LPERMCO'],
                                        downcast = 'integer', errors = 'coerce')

    # Drop other variables
    linktable = linktable.drop(['LPERMNO', 'LPERMCO', 'LINKDT', 'LINKENDDT', 'conm', 'CONML'], axis=1).drop_duplicates()
    #--------------------------------------

    tnic3hhi_linked = tnic3hhi.merge(linktable.add_suffix('1'),
                                     on='gvkey1', how='inner')

    tnic3hhi_linked = tnic3hhi_linked.merge(linktable.add_suffix('2'),
                                            on='gvkey2', how='inner')


    tnic3hhi_linked = tnic3hhi_linked[
        (tnic3hhi_linked.linkdt1.dt.year<=tnic3hhi_linked.year) & \
            (tnic3hhi_linked.year<=tnic3hhi_linked.linkenddt1.dt.year) & \
                (tnic3hhi_linked.linkdt2.dt.year<=tnic3hhi_linked.year) & \
                    (tnic3hhi_linked.year<=tnic3hhi_linked.linkenddt2.dt.year)
        ]

    tnic3hhi_linked[['gvkey1', 'gvkey2', 'year']].value_counts().value_counts()
    # =============================================================================
    # 1     2396920
    # 2       58785
    # 4        3397
    # 3        2054
    # 6         276
    # 5         101
    # 8          70
    # 12         17
    # 10          7
    # 9           7
    # dtype: int64
    # =============================================================================

    #tnic3hhi_linked[['gvkey1', 'gvkey2', 'year']].value_counts()
    #tnic3hhi_linked[(tnic3hhi_linked.gvkey1==21227)&(tnic3hhi_linked.gvkey2==17010)&(tnic3hhi_linked.year==2016)]
    # => more observations due to non-unique permno

    tnic3hhi_permco = tnic3hhi_linked[['gvkey1', 'permco1', 'gvkey2', 'permco2', 'year']].\
        drop_duplicates().reset_index(drop=True)

    tnic3hhi_permco[['gvkey1', 'gvkey2', 'year']].value_counts().value_counts(normalize=True)
    # =============================================================================
    # 1    0.997160
    # 2    0.002837
    # 4    0.000003
    # dtype: float64
    # =============================================================================
    # => almost unique, leave with that

    tnic3hhi_permco = tnic3hhi_permco.drop_duplicates(['permco1', 'permco2', 'year']).reset_index(drop=True)

    #tnic3hhi_permco_save = tnic3hhi_permco.copy()
    #tnic3hhi_permco = tnic3hhi_permco.iloc[0:100000,:]

    # Create list of tuples of peers and permco1: !!! Too slow !!!!
    #own_and_peer_permcos = []
    #for permco1 in tnic3hhi_permco.permco1:
    #    for year in tnic3hhi_permco[tnic3hhi_permco.permco1==permco1].year.unique():
    #        own_and_peer_permcos.append((permco1, year,
    #                                     tnic3hhi_permco[
    #                                         (tnic3hhi_permco.permco1==permco1) &
    #                                         (tnic3hhi_permco.year==year)].permco2.tolist()))

    return tnic3hhi_permco

#-------------------------------
# Create and Save peer list
#-------------------------------

if not('tnic3_close_peers.csv' in OUTPUT_PATH):
    own_and_peer_permcos_global = _close_peer_construction()

    own_and_peer_permcos_global.to_csv(OUTPUT_PATH+'/tnic3_close_peers.csv',
                                index=False, encoding='utf-8')

#else:
#    own_and_peer_permcos_global = pd.read_csv(
#        OUTPUT_PATH+'/tnic3_close_peers.csv',
#        encoding='utf-8')
# => not needed since close competitors are loaded in function

#================================================
# Construct measure of technological closeness
#================================================


#============================================
from sklearn.metrics.pairwise import cosine_similarity

# %%
#================================================
#def close_peers_technology_proximity(search_year, OUTPUT_PATH, LOAD_VERSION, VERSION):
def close_peers_technology_proximity(search_year):
    print('Start extraction of full text for applications for \n year ' + str(search_year) + '\n', flush=True)
    # Error log is last element to be written out, thus check if already in directory or not
    if not('error_log_close_peers_'+str(search_year)+'_v'+str(VERSION)+'.csv' in os.listdir(OUTPUT_PATH)):
        '''Wrapper for calculating technological proximity to peers'''

        #*********************************************
        print('Load close peer data for for year {0}'.format(str(search_year)), flush=True)
        # Load close peers
        own_and_peer_permcos = pd.read_csv(OUTPUT_PATH+'/tnic3_close_peers.csv',
                                                  encoding='utf-8', low_memory=False)

        own_and_peer_permcos = own_and_peer_permcos[own_and_peer_permcos.year==search_year]
        own_permcos = own_and_peer_permcos.permco1.unique().tolist()
        peer_permcos = own_and_peer_permcos.permco2.unique().tolist()


        #*********************************************
        # Note, we only need a certain subcategories of the large patent_citation file, thus
        # load in chunks and only save the relevant portions
        print('Load citations data for year {0}'.format(str(search_year)), flush=True)

        neede_columns = [
            'patent_id', 'citation_id',
            'section', 'class', 'sub_class', 'maingroup',
            'section_cited','class_cited', 'sub_class_cited', 'maingroup_cited',
            'filing_date_dt', 'issue_date_dt', 'filing_year', 'issue_year', 'permco',
            'filing_date_dt_cited', 'issue_date_dt_cited', 'filing_year_cited',
            'issue_year_cited', 'permco_cited'
            ]

        chunksize = 10e6
        patent_citation_with_kpss = pd.DataFrame()
        for chunk in pd.read_csv(OUTPUT_PATH+'/PatentsView_patent_citation_'+str(LOAD_VERSION)+'.csv',
                                 encoding='utf-8', chunksize=chunksize):

            append_df = chunk[neede_columns]

            #=====================================================
            # Post loading data casting
            append_df['permco'] = pd.to_numeric(
                    append_df.permco,
                    downcast = 'integer', errors = 'coerce')

            append_df['permco_cited'] = pd.to_numeric(
                append_df.permco_cited,
                downcast = 'integer', errors = 'coerce')

            #-----------------------------------------------------
            # Limit to relevant time frame
            append_df['filing_date_dt'] = pd.to_datetime(append_df['filing_date_dt'])
            append_df[append_df.filing_year==search_year]

            #-----------------------------------------------------
            # Limit to relevant identifiers
            append_df = append_df[
                (append_df.permco.isin(own_permcos))|\
                (append_df.permco_cited.isin(own_permcos))|\
                (append_df.permco.isin(peer_permcos))|\
                (append_df.permco_cited.isin(peer_permcos))]

            #=====================================================
            patent_citation_with_kpss = patent_citation_with_kpss.append(
                append_df,
                ignore_index=True
                )

        #****************************************************************
        print('Load classification data for year {0}'.format(str(search_year)), flush=True)
        kpss_ipc_data = pd.read_csv(OUTPUT_PATH+'/KPSS_ipc_classes_'+str(LOAD_VERSION)+'.csv',
                                    encoding='utf-8')

        #=====================================================
        # Post loading structuring

        # Drop na values from class definition and define date
        kpss_ipc_data = kpss_ipc_data[~kpss_ipc_data.maingroup.isna()]

        # For annual technology proximity calculation
        kpss_ipc_data['filing_date_dt'] = pd.to_datetime(kpss_ipc_data['filing_date_dt'],
                                                         errors='coerce')
        kpss_ipc_data['search_date_dt'] = kpss_ipc_data.filing_date_dt.dt.year

        kpss_ipc_data['quarter_end_date'] = kpss_ipc_data.filing_date_dt + pd.offsets.QuarterEnd(0)
        kpss_ipc_data = kpss_ipc_data.reset_index(drop=True)

        kpss_ipc_data = kpss_ipc_data[
            (kpss_ipc_data.search_date_dt<=search_year) & \
            (kpss_ipc_data.permco.isin(own_permcos))|\
            (kpss_ipc_data.search_date_dt<=search_year) & \
            (kpss_ipc_data.permco.isin(peer_permcos))]

        #****************************************************************
        # Here, actual routine starts
        #-------------------------------
        # Create output dataframes
        cited_by_competitor_df = pd.DataFrame()
        citing_a_competitor_df = pd.DataFrame()
        common_citations_own_patents_df = pd.DataFrame()
        total_citations_own_patents_df = pd.DataFrame()

        citation_proximity_to_peers_df = pd.DataFrame()

        error_log = pd.DataFrame(columns = ['permco1', 'year', 'error'])

        # !!! keep track of already observed files via peer count dataframe !!!
        if not('Close_peers_technology_proximity_peer_count_'+str(search_year)+'.csv' in OUTPUT_PATH):
            peer_count_df = pd.DataFrame(columns=['permco1', 'year', 'num_peers'])
            
            already_processed_permco1 = []
        else:
            peer_count_df = pd.read_csv(
                OUTPUT_PATH+'/Close_peers_technology_proximity_peer_count_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                encoding='utf-8', low_memory=False)
            error_log = pd.read_csv(
                OUTPUT_PATH+'/intermediate_error_log_close_peers_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                encoding='utf-8', low_memory=False)
                    
            already_processed_permco1 = peer_count_df.permco1.tolist()
        #========================================
        # Linear execution per permco - year
        #========================================
        for permco1 in own_and_peer_permcos.permco1.unique():
            try:
                #***********************************************
                if (permco1 in already_processed_permco1):
                    print('\t\t similarity already constructed for {0}, year {1}, skip'.format(str(permco1), str(search_year)), flush=True)    
                    continue
                    
                #for year in own_and_peer_permcos[own_and_peer_permcos.permco1==permco1].year.unique():
                print('\t construct competitors similarity now for {0}, year {1}'.format(str(permco1), str(search_year)), flush=True)
                #==============================================
                # 0) Sice of peer group (year already verified by handover of local dataframe)
                peers = own_and_peer_permcos[(own_and_peer_permcos.permco1==permco1)].permco2.tolist()

                number_peers = len(peers)

                peer_count_df.loc[len(peer_count_df)] = [permco1, search_year, number_peers]

                #==============================================
                # 1) Being cited by close competitors:
                cited_by_competitor = patent_citation_with_kpss[
                    (patent_citation_with_kpss.permco_cited == permco1) & \
                    (patent_citation_with_kpss.permco.isin(peers)) & \
                    (patent_citation_with_kpss.permco.notna()) & (patent_citation_with_kpss.permco_cited.notna()) & \
                    (patent_citation_with_kpss.permco!='') & (patent_citation_with_kpss.permco_cited!='')
                    ][['citation_id', 'patent_id']].\
                    drop_duplicates().groupby(['citation_id']).size().reset_index(drop=False).\
                        rename(columns={0:'cited_by_competitor_citations',
                                            'citation_id':'patent_id'})

                cited_by_competitor['permco1'] = permco1
                cited_by_competitor['year'] = search_year
                cited_by_competitor_df = cited_by_competitor_df.append(cited_by_competitor, ignore_index=True)

                #=========================================
                # 2) Citing a close competitors:
                citing_a_competitor = patent_citation_with_kpss[
                    (patent_citation_with_kpss.permco == permco1) & \
                    (patent_citation_with_kpss.permco_cited.isin(peers)) & \
                    (patent_citation_with_kpss.permco.notna()) & (patent_citation_with_kpss.permco_cited.notna()) & \
                    (patent_citation_with_kpss.permco!='') & (patent_citation_with_kpss.permco_cited!='')
                    ][['citation_id', 'patent_id']].\
                    drop_duplicates().groupby(['patent_id']).size().reset_index(drop=False).\
                        rename(columns={0:'citing_a_competitor_citations'})

                citing_a_competitor['permco1'] = permco1
                citing_a_competitor['year'] = search_year
                citing_a_competitor_df = citing_a_competitor_df.append(citing_a_competitor, ignore_index=True)


                #==============================================
                # 3) Citing same patents:
                own_patents = patent_citation_with_kpss[
                    (patent_citation_with_kpss.permco == permco1) & \
                    (patent_citation_with_kpss.permco.notna()) & \
                    (patent_citation_with_kpss.permco!='')
                    ][['citation_id', 'patent_id']].\
                    drop_duplicates().add_prefix('own_patents_')

                peer_patents = patent_citation_with_kpss[
                    (patent_citation_with_kpss.permco.isin(peers)) & \
                    (patent_citation_with_kpss.permco.notna()) & \
                    (patent_citation_with_kpss.permco!='')
                    ][['citation_id', 'patent_id']].\
                    drop_duplicates().add_prefix('peer_patents_')

                # Merge and find common citations
                common_citations = own_patents.merge(peer_patents,
                                                     left_on=['own_patents_citation_id'],
                                                     right_on=['peer_patents_citation_id'],
                                                     how='inner')

                # Aggregate counts
                common_citations_own_patents = common_citations.\
                    groupby('own_patents_patent_id').size().reset_index(drop=False).\
                        rename(columns={0:'common_citations_with_peers_citations',
                                        'own_patents_patent_id':'patent_id'})

                total_citations_own_patents = own_patents.\
                    groupby(['own_patents_patent_id']).size().reset_index(drop=False).\
                        rename(columns={0:'total_citations',
                                        'own_patents_patent_id':'patent_id'})

                common_citations_own_patents['permco1'] = permco1
                common_citations_own_patents['year'] = search_year
                common_citations_own_patents_df = common_citations_own_patents_df.append(
                    common_citations_own_patents, ignore_index=True)

                total_citations_own_patents['permco1'] = permco1
                total_citations_own_patents['year'] = search_year
                total_citations_own_patents_df = total_citations_own_patents_df.append(
                    total_citations_own_patents, ignore_index=True)

                # !!! within classes now !!!
                for class_type in ['section', 'class', 'sub_class', 'maingroup']:
                    #==============================================
                    # 4) Citing same patents:
                    # => current_date already defined as year when loading data

                    current_patents_own_patents = kpss_ipc_data[
                        (kpss_ipc_data.search_date_dt==search_year) & \
                        (kpss_ipc_data.permco==permco1)
                        ][['patent_id', class_type]].drop_duplicates()
                    previous_patents_own_patents = kpss_ipc_data[
                        (kpss_ipc_data.search_date_dt<search_year) & \
                        (kpss_ipc_data.permco==permco1)
                        ][['patent_id', class_type]].drop_duplicates()

                    current_patents_peer_patents = kpss_ipc_data[
                        (kpss_ipc_data.search_date_dt==search_year) & \
                        (kpss_ipc_data.permco.isin(peers))
                        ][['patent_id', class_type]].drop_duplicates()
                    previous_patents_peer_patents = kpss_ipc_data[
                        (kpss_ipc_data.search_date_dt<search_year) & \
                        (kpss_ipc_data.permco.isin(peers))
                        ][['patent_id', class_type]].drop_duplicates()


                    #-----------------------------------
                    # => count based on key and patent_class
                    group_count_current_patents_own_patents = current_patents_own_patents.groupby([class_type]).count().\
                        reset_index().rename(columns={'patent_id':'count'})

                    group_count_previous_patents_own_patents = previous_patents_own_patents.groupby([class_type]).count().\
                        reset_index().rename(columns={'patent_id':'count'})

                    group_count_current_patents_peer_patents = current_patents_peer_patents.groupby([class_type]).count().\
                        reset_index().rename(columns={'patent_id':'count'})

                    group_count_previous_patents_peer_patents = previous_patents_peer_patents.groupby([class_type]).count().\
                        reset_index().rename(columns={'patent_id':'count'})

                    #-----------------------------------
                    # Merge to table with all counts
                    group_count_own_patents = group_count_current_patents_own_patents.merge(
                        group_count_previous_patents_own_patents,
                        on=[class_type],
                        how='outer',
                        suffixes=['_current', '_previous'])

                    group_count_peer_patents = group_count_current_patents_peer_patents.merge(
                        group_count_previous_patents_peer_patents,
                        on=[class_type],
                        how='outer',
                        suffixes=['_current', '_previous'])

                    group_count_all = group_count_own_patents.merge(
                        group_count_peer_patents,
                        on=[class_type],
                        how='outer',
                        suffixes=['_own', '_peer'])

                    #----------------------------------
                    # Fill zeros
                    group_count_all = group_count_all.fillna(0)

                    #----------------------------------
                    # Calculate cosine similarities
                    def _cosine_sim(a,b):

                        dot_prod = sum(i[0] * i[1] for i in zip(a, b))
                        a_square = sum(i[0] * i[1] for i in zip(a, a))
                        b_square = sum(i[0] * i[1] for i in zip(b, b))

                        if (b_square>0) & (a_square>0):
                            return(dot_prod / (a_square**(1/2)*b_square**(1/2)))
                        else:
                            return(np.nan)

                    citation_proximity_own_patents = _cosine_sim(group_count_all.count_current_own, group_count_all.count_previous_own)
                    citation_proximity_peer_patents = _cosine_sim(group_count_all.count_current_peer, group_count_all.count_previous_peer)

                    citation_proximity_to_peers_current_patents = _cosine_sim(group_count_all.count_current_own, group_count_all.count_current_peer)
                    citation_proximity_to_peers_previous_patents = _cosine_sim(group_count_all.count_previous_own, group_count_all.count_previous_peer)


                    #===========================================
                    # 5) measure from  Lyandres, Palazzo, 2016
                    limited_citation = patent_citation_with_kpss[
                        patent_citation_with_kpss.filing_year_cited>=(patent_citation_with_kpss.issue_year_cited-3)
                        ]
                    limited_citation = limited_citation[(limited_citation.permco_cited.notna()) & \
                                                        (limited_citation.permco_cited!='') & \
                                                        (~limited_citation[class_type].isna())]

                    limited_citation_own = limited_citation[(limited_citation.permco_cited == permco1) & \
                                                            (limited_citation.issue_year <= (limited_citation.issue_year_cited+3))]

                    limited_citation_peer = limited_citation[(limited_citation.permco_cited.isin(peers)) & \
                                                            (limited_citation.issue_year <= (limited_citation.issue_year_cited+3))]

                    #------------------------------------------
                    # Group by technology class
                    limited_citation_peer_class_groups = limited_citation_peer[['citation_id', 'patent_id', class_type]].\
                        drop_duplicates().groupby([class_type]).size().reset_index(drop=False).\
                            rename(columns={0:'cited_in_class_peer'}).fillna(0)

                    limited_citation_own_class_groups = limited_citation_own[['citation_id', 'patent_id', class_type]].\
                        drop_duplicates().groupby([class_type]).size().reset_index(drop=False).\
                            rename(columns={0:'cited_in_class_own'}).fillna(0)

                    #------------------------------------------
                    # Merge and calculate intersect
                    limited_citations_groups = limited_citation_own_class_groups.merge(
                        limited_citation_peer_class_groups,
                        on=[class_type],
                        how='outer').fillna(0)

                    limited_citations_groups['min'] = limited_citations_groups[['cited_in_class_peer', 'cited_in_class_own']].min(axis=1)

                    sum_peer = limited_citations_groups['cited_in_class_peer'].sum()
                    sum_own = limited_citations_groups['cited_in_class_own'].sum()

                    sum_min = limited_citations_groups['min'].sum()

                    gamma = sum_min / (max(sum_peer, sum_own))

                    #------------------------------------
                    # Save in dataframe
                    citation_proximity_to_peers = pd.DataFrame(columns=['year', 'permco1', 'class_type',
                                                                        'citations_within_own', 'citations_within_peer',
                                                                        'citations_to_peer_current', 'citations_to_peer_previous', 'gamma'])

                    citation_proximity_to_peers.loc[0] = [search_year, permco1, class_type, citation_proximity_own_patents,
                                                          citation_proximity_peer_patents, citation_proximity_to_peers_current_patents,
                                                          citation_proximity_to_peers_previous_patents, gamma]

                    citation_proximity_to_peers_df = citation_proximity_to_peers_df.append(
                        citation_proximity_to_peers, ignore_index=True)
                    
                #************************************************************
                # intermediate save 
                if len(peer_count_df) % 50 == 0:
                    cited_by_competitor_df.to_csv(
                           OUTPUT_PATH+'/Close_peers_technology_proximity_cited_by_competitor_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                           index=False, encoding='utf-8')
                    citing_a_competitor_df.to_csv(
                           OUTPUT_PATH+'/Close_peers_technology_proximity_citing_a_competitor_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                           index=False, encoding='utf-8')
                    common_citations_own_patents_df.to_csv(
                           OUTPUT_PATH+'/Close_peers_technology_proximity_common_citations_own_patents_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                           index=False, encoding='utf-8')
                    total_citations_own_patents_df.to_csv(
                           OUTPUT_PATH+'/Close_peers_technology_proximity_total_citations_own_patents_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                           index=False, encoding='utf-8')
            
                    citation_proximity_to_peers_df.to_csv(
                           OUTPUT_PATH+'/Close_peers_technology_proximity_total_citation_proximity_to_peers_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                           index=False, encoding='utf-8')
            
                    peer_count_df.to_csv(OUTPUT_PATH+'/Close_peers_technology_proximity_peer_count_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                                            index=False, encoding='utf-8')
            
                    #!!! Note that to check if the execution is already complete, I check for the 
                    # presence of the error_log_close_peers file; thus save only intermediate values
                    # up to the completed execution
                    error_log.to_csv(OUTPUT_PATH+'/intermediate_error_log_close_peers_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                                            index=False, encoding='utf-8')
                    
            #---------------------------------------------
            except Exception as exc:
                print('\t\t Error in construct competitors similarity \n\
                      for {0}, year {1}: \n\ {2}'.format(str(permco1), str(search_year), str(exc)), flush=True)
                error_log.loc[len(error_log)] = [permco1, search_year, str(exc)]
            
            
        #============================================
        # Final save after routine
        cited_by_competitor_df.to_csv(
               OUTPUT_PATH+'/Close_peers_technology_proximity_cited_by_competitor_'+str(search_year)+'_v'+str(VERSION)+'.csv',
               index=False, encoding='utf-8')
        citing_a_competitor_df.to_csv(
               OUTPUT_PATH+'/Close_peers_technology_proximity_citing_a_competitor_'+str(search_year)+'_v'+str(VERSION)+'.csv',
               index=False, encoding='utf-8')
        common_citations_own_patents_df.to_csv(
               OUTPUT_PATH+'/Close_peers_technology_proximity_common_citations_own_patents_'+str(search_year)+'_v'+str(VERSION)+'.csv',
               index=False, encoding='utf-8')
        total_citations_own_patents_df.to_csv(
               OUTPUT_PATH+'/Close_peers_technology_proximity_total_citations_own_patents_'+str(search_year)+'_v'+str(VERSION)+'.csv',
               index=False, encoding='utf-8')

        citation_proximity_to_peers_df.to_csv(
               OUTPUT_PATH+'/Close_peers_technology_proximity_total_citation_proximity_to_peers_'+str(search_year)+'_v'+str(VERSION)+'.csv',
               index=False, encoding='utf-8')

        peer_count_df.to_csv(OUTPUT_PATH+'/Close_peers_technology_proximity_peer_count_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                                index=False, encoding='utf-8')

        error_log.to_csv(OUTPUT_PATH+'/error_log_close_peers_'+str(search_year)+'_v'+str(VERSION)+'.csv',
                                index=False, encoding='utf-8')

        print('End of close competitors construction routine for year {0}'.\
              format(str(search_year)), flush=True)
    #--------------------------------------------
    else:
        print('Error log for close peers already in directory, skip for year {0}'.\
            format(str(search_year)), flush=True)
    return


# %%
# !!! Execute only when needed
#-------------------------------------------------
# Parallel execution
#-------------------------------------------------
n_cores = mp.cpu_count()
print('\t\t Number of Cores: ' + str(n_cores), flush=True)

#pool = mp.Pool(n_cores)
pool = mp.Pool(5)
pool.map_async(close_peers_technology_proximity, range(1990,2020))
pool.close()
pool.join()

r'''
# Method with apply async
pool = mp.Pool(6)
for c_year in range(1990,2020):
    pool.apply_async(
                close_peers_technology_proximity,
                args=(c_year, )
            )
pool.close()
pool.join()
r'''

#linear test
#close_peers_technology_proximity(2000)

# %%
###############################################
# Local Execution
###############################################
r'''
import pandas as pd
import csv

KPSS_public = pd.read_csv(source_directory + '//KPSS 2020 data///KPSS_public.csv')
KPSS_public['issue_date_dt'] = pd.to_datetime(KPSS_public['issue_date'], format='%m/%d/%Y')
KPSS_public['issue_year'] = KPSS_public.issue_date_dt.dt.year
KPSS_public['filing_date_dt'] = pd.to_datetime(KPSS_public['filing_date'], format='%m/%d/%Y')
KPSS_public['filing_year'] = KPSS_public.filing_date_dt.dt.year
KPSS_public['grant_doc_num'] = pd.to_numeric(KPSS_public.patent_num,
                                                  downcast = 'integer', errors = 'coerce')

# !!! Note that the issue dates of the cited patents in uspatentcitations is
# the normalized to be the first day of the issue month
KPSS_public['issue_date_dt_month_kpss'] = KPSS_public['issue_date_dt'] + pd.offsets.MonthBegin(0)


#KPSS_public['in_uspc'] = KPSS_public.apply(lambda x: bool(x.grant_doc_num in (list(set(uspc_current.patent_id.to_list())))), axis=1)

kpss_merge = KPSS_public[
    ['grant_doc_num', 'xi_real',
     'xi_nominal', 'cites',
     'filing_date_dt', 'issue_date_dt',
     'filing_year', 'issue_year',
     'issue_date_dt_month_kpss']
    ].drop_duplicates()

patent_permco_permno_match_public = pd.read_csv(source_directory + '//patent_permco_permno_match_public.csv')
#patent_permco_permno_match_public.patent_num.value_counts().value_counts()
# => unique

# Coerce data types
patent_permco_permno_match_public['grant_doc_num'] = pd.to_numeric(
    patent_permco_permno_match_public.patent_num,
    downcast = 'integer', errors = 'coerce')
patent_permco_permno_match_public['permco'] = pd.to_numeric(
    patent_permco_permno_match_public.permco,
    downcast = 'integer', errors = 'coerce')
patent_permco_permno_match_public['permno'] = pd.to_numeric(
    patent_permco_permno_match_public.permno,
    downcast = 'integer', errors = 'coerce')

# Merge with permco link (left merge to allow for non-permco matched data)
kpss_complete = pd.merge(kpss_merge,
                         patent_permco_permno_match_public.\
                             drop(['patent_num'], axis=1).drop_duplicates(),
                         on='grant_doc_num',
                         how='left')


ipcr = pd.read_csv(r"C:\Users\domin\Downloads\ipcr.tsv\ipcr.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC)
ipcr = ipcr.drop('uuid', axis=1)
ipcr = ipcr[ipcr.sequence==0]

ipcr['patent_id'] = pd.to_numeric(
    ipcr.patent_id,
    downcast = 'integer', errors = 'coerce')


ipcr.ipc_version_indicator.value_counts(normalize=True)
# => 90% in format of 2006

ipcr.classification_status.value_counts(normalize=True)
# All B

ipcr.symbol_position.value_counts(normalize=True)
# => 98.8% First or sole invention information


ipcr['test_class'] = ipcr.section.astype(str) + '_' + ipcr.ipc_class.astype(str).apply(lambda x: x.split('.')[0])
#\
#    + '_' + ipcr.subclass.astype(str).apply(lambda x: x.split('.')[0])

len(ipcr['test_class'].unique())
# 1005
ipcr['test_class'].value_counts(normalize=True).describe()
#count    1.005000e+03
#mean     9.950249e-04
#std      5.985173e-03
#min      1.405511e-07
#25%      1.405511e-07
#50%      5.622046e-07
#75%      4.638188e-06
#max      1.059442e-01
#Name: test_class, dtype: float64



kpss_complete_classes = kpss_complete.rename(columns={'grant_doc_num':'patent_id'}).merge(
        ipcr,
        how='left',
        on='patent_id')

year_a = kpss_complete_classes[~kpss_complete_classes.ipc_class.isnull()]['filing_year'].value_counts().reset_index()
year_b = kpss_complete_classes['filing_year'].value_counts().reset_index()

test_year = year_a.merge(year_b, on='index', how='right')
test_year['rel'] = test_year.filing_year_x / test_year.filing_year_y
test_year = test_year.sort_values('index', ascending=False)

test_year.iloc[0:50]

uspc = pd.read_csv(r"C:\Users\domin\Downloads\uspc.tsv\uspc.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC)
uspc = uspc.drop('uuid', axis=1)
uspc = uspc[uspc.sequence==0]

uspc['patent_id'] = pd.to_numeric(
    uspc.patent_id,
    downcast = 'integer', errors = 'coerce')


len(uspc.mainclass_id.unique())
# 1016

uspc.mainclass_id.value_counts(normalize=True).describe()
#count    1.016000e+03
#mean     9.842520e-04
#std      2.129511e-03
#min      1.972894e-07
#25%      5.918682e-07
#50%      1.262652e-05
#75%      1.029456e-03
#max      1.982680e-02
#Name: mainclass_id, dtype: float64

kpss_complete_classes = kpss_complete_classes.rename(columns={'grant_doc_num':'patent_id'}).merge(
        uspc,
        how='left',
        on='patent_id')

year_a = kpss_complete_classes[~kpss_complete_classes.mainclass_id.isnull()]['filing_year'].value_counts().reset_index()
year_b = kpss_complete_classes['filing_year'].value_counts().reset_index()

test_year = year_a.merge(year_b, on='index', how='right')
test_year['rel'] = test_year.filing_year_x / test_year.filing_year_y
test_year = test_year.sort_values('index', ascending=False)

test_year.iloc[0:50]


kpss_complete_classes.mainclass_id.value_counts(normalize=True).describe()
# =============================================================================
# count    8.070000e+02
# mean     1.239157e-03
# std      3.002361e-03
# min      5.780928e-07
# 25%      1.156186e-06
# 50%      6.359021e-05
# 75%      9.480722e-04
# max      2.822191e-02
# Name: mainclass_id, dtype: float64
# =============================================================================


kpss_complete_classes['ipc_test_class'] = kpss_complete_classes.section.astype(str) + '_' + kpss_complete_classes.ipc_class.astype(str).apply(lambda x: x.split('.')[0])
kpss_complete_classes.ipc_test_class.value_counts(normalize=True).describe()
# =============================================================================
# count    6.510000e+02
# mean     1.536098e-03
# std      1.111774e-02
# min      3.389480e-07
# 25%      3.389480e-07
# 50%      1.355792e-06
# 75%      5.253694e-05
# max      2.122482e-01
# Name: ipc_test_class, dtype: float64
# =============================================================================
# => but more skewed, but overall very similar



# %%
##########################################################
# Citation based technology proximity measure            #
##########################################################
import pandas as pd
import numpy as np
import re
import os

pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 120)



patent_citation_with_kpss = pd.read_csv(r"C:\Users\domin\Desktop\PatentsView_patent_citation_3.csv", nrows=1e6)

#=======================================
# Load hoberg philips close peers
# Directory for HP data
hp_directory = r'C:\Users\domin\Google Drive\Preliminary Research\Alice and Innovation Project\Hoberg_Phillips_data'

tnic3hhi = pd.read_csv(hp_directory + '/tnic3_data.txt', delimiter="\t")

# Exclude self references
tnic3hhi = tnic3hhi[(tnic3hhi.gvkey1!=tnic3hhi.gvkey2)]

# Limit to closes competitors
N_CLOSE_COMPETITORS = 20
tnic3hhi = tnic3hhi.sort_values('score', ascending=False).\
            groupby(['gvkey1', 'year']).head(N_CLOSE_COMPETITORS).reset_index(drop=False).drop('index', axis=1)

#-----------------------------------
# Use linktable to link to permco
source_directory = r'C:\Users\domin\Google Drive\Preliminary Research\Alice and Innovation Project\Patent Portfolio and Economic Data\Patent_portfolio_structuring_source_directory'

linktable = pd.read_csv(source_directory + '//crsp_ccm_link.csv')
linktable = linktable[['gvkey', 'LPERMNO', 'LPERMCO', 'cusip',
                       'LINKDT', 'LINKENDDT', 'tic',
                       'conm', 'CONML', 'WEBURL']]

# Change link end and start dates to date format
linktable['linkdt'] = pd.to_datetime(linktable['LINKDT'], format='%Y%m%d', errors='coerce')
linktable['linkenddt'] = pd.to_datetime(linktable['LINKENDDT'], format='%Y%m%d', errors='coerce')

# if linkenddt is missing then set to first of 2020
linktable['linkenddt'] = linktable['linkenddt'].fillna(pd.to_datetime('20200101', format='%Y%m%d'))

# define permco and permno as string
linktable['permno'] = pd.to_numeric(linktable['LPERMNO'],
                                    downcast = 'integer', errors = 'coerce')
linktable['permco'] = pd.to_numeric(linktable['LPERMCO'],
                                    downcast = 'integer', errors = 'coerce')

# Drop other variables
linktable = linktable.drop(['LPERMNO', 'LPERMCO', 'LINKDT', 'LINKENDDT', 'conm', 'CONML'], axis=1).drop_duplicates()
#--------------------------------------

tnic3hhi_linked = tnic3hhi.merge(linktable.add_suffix('1'),
                                 on='gvkey1', how='inner')

tnic3hhi_linked = tnic3hhi_linked.merge(linktable.add_suffix('2'),
                                        on='gvkey2', how='inner')


tnic3hhi_linked = tnic3hhi_linked[
    (tnic3hhi_linked.linkdt1.dt.year<=tnic3hhi_linked.year) & \
        (tnic3hhi_linked.year<=tnic3hhi_linked.linkenddt1.dt.year) & \
            (tnic3hhi_linked.linkdt2.dt.year<=tnic3hhi_linked.year) & \
                (tnic3hhi_linked.year<=tnic3hhi_linked.linkenddt2.dt.year)
    ]

tnic3hhi_linked[['gvkey1', 'gvkey2', 'year']].value_counts().value_counts()
# =============================================================================
# 1     2396920
# 2       58785
# 4        3397
# 3        2054
# 6         276
# 5         101
# 8          70
# 12         17
# 10          7
# 9           7
# dtype: int64
# =============================================================================

#tnic3hhi_linked[['gvkey1', 'gvkey2', 'year']].value_counts()
#tnic3hhi_linked[(tnic3hhi_linked.gvkey1==21227)&(tnic3hhi_linked.gvkey2==17010)&(tnic3hhi_linked.year==2016)]
# => more observations due to non-unique permno

tnic3hhi_permco = tnic3hhi_linked[['gvkey1', 'permco1', 'gvkey2', 'permco2', 'year']].\
    drop_duplicates().reset_index(drop=True)

tnic3hhi_permco[['gvkey1', 'gvkey2', 'year']].value_counts().value_counts(normalize=True)
# =============================================================================
# 1    0.997160
# 2    0.002837
# 4    0.000003
# dtype: float64
# =============================================================================
# => almost unique, leave with that

#------------------------------------------
# Load citation matrix

import scipy.sparse
import pickle
from pandas.api.types import CategoricalDtype

citation_matrix = scipy.sparse.load_npz("patent_citation_matrix_complete_3.npz")

# unpickle categories
with open(r"C:\Users\domin\Desktop\patent_citation_matrix_complete__patent_id_c___3.pkl", 'rb') as fp:
    patent_id_c = pickle.load(fp)
with open(r"C:\Users\domin\Desktop\patent_citation_matrix_complete__citation_id_c___3.pkl", 'rb') as fp:
    citation_id_c = pickle.load(fp)


#=======================================

patents_to_search = patents_view_citations[patents_view_citations.permco==90]['patent_id'].tolist()


location = np.where(patent_id_c.categories.isin(patents_to_search))

citation_id_c.categories[np.where(citation_matrix[location].toarray()[0]==1)]

patent_id_c


# => close competitors cite each other (receive citations and does citations)
# respective current year, quarter, and past
# pairwise, if possible


# => Cite same patents in applications (third party)
# respective current year, quarter, and past
# => pairwise, if possible, to allow for asymmetry analysis

# => filing in same technology classes
# respective current year, quarter, and past
# => pairwise, if possible, to allow for asymmetry analysis

# => Lyandres, Palazzo, 2016
# citations received from same patents/same technology class

r'''

#test = pd.read_csv(r"C:\Users\domin\Desktop\Close_peers_technology_proximity_total_citation_proximity_to_peers_2005.csv")
#test[test.class_type=='section'].gamma.describe()
