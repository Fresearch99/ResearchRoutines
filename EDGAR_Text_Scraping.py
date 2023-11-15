"""
    DATE: 11/14/2023
    METHOD: Program to download EDGAR text files

    Code based on:
    ND-SRAF / McDonald : 201606
    https://sraf.nd.edu
"""

import os
import csv
import pandas as pd
import re
import time

import unicodedata

import requests
from bs4 import BeautifulSoup
from lxml import html

#from multiprocessing import Pool, cpu_count

import urllib3
#Disable warnings for scraping
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


HEADER = {'Host': 'www.sec.gov', 'Connection': 'close',
         'Accept': 'application/json, text/javascript, */*; q=0.01', 'X-Requested-With': 'XMLHttpRequest',
         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
         }

# Modify the following statement to identify the path for local modules
# sys.path.append('C:/Users/domin/Desktop/Second_Year_Paper/Loughran-McDonald Text Mining Suit/Python Code')
# Since these imports are dynamically mapped your IDE might flag an error...it's OK


# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * +

#  NOTES
#        The EDGAR archive contains millions of forms.
#        For details on accessing the EDGAR servers see:
#          https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm
#        From that site:
#            "To preserve equitable server access, we ask that bulk FTP
#             transfer requests be performed between 9 PM and 6 AM Eastern
#             time. Please use efficient scripting, downloading only what you
#             need and space out requests to minimize server load."
#        Note that the program will check the clock every 10 minutes and only
#            download files during the appropriate time.
#
#        For large downloads you will sometimes get a hiccup in the server
#            and the file request will fail.  These errs are documented in
#            the log file.  You can manually download those files that fail.
#            Although I attempt to work around server errors, if the SEC's server
#            is sufficiently busy, you might have to try another day.
#
#       For a list of form types and counts by year:
#         "All SEC EDGAR Filings by Type and Year"
#          at https://sraf.nd.edu/sec-edgar-data/



#######################################################
#
#   Function definitions
#
#######################################################

def download_masterindex(year, qtr, flag=False):
    # Download Master.idx from EDGAR
    # Loop accounts for temporary server/ISP issues
    # ND-SRAF / McDonald : 201606

    from zipfile import ZipFile
    from io import BytesIO

    number_of_tries = 5
    sleep_time = 5  # Note sleep time accumulates according to err


    PARM_ROOT_PATH = 'https://www.sec.gov/Archives/edgar/full-index/'

    masterindex = []
   
    #  using the zip file is a little more complicated but orders of magnitude faster
    append_path = str(year) + '/QTR' + str(qtr) + '/master.zip'  # /master.idx => nonzip version
    sec_url = PARM_ROOT_PATH + append_path

    for i in range(1, number_of_tries + 1):
        try:
            response = requests.get(sec_url, headers=HEADER)
            if not(response.ok):
                continue
            zipfile = ZipFile(BytesIO(response.content))
            records = zipfile.open('master.idx').read().decode('utf-8', 'ignore').splitlines()[10:]
            #records = urlopen(sec_url).read().decode('utf-8').splitlines()[10:] #  => nonzip version
            break
        except Exception as exc:
            if i == 1:
                print('\nError in download_masterindex')
            print('  {0}. _url:  {1}'.format(i, sec_url))

            if '404' in str(exc):
                break
            if i == number_of_tries:
                return False
            time.sleep(sleep_time)



    # Load m.i. records into masterindex list
    for line in records:
        mir = MasterIndexRecord(line)
        if not mir.err:
            masterindex.append(mir)

    if flag:
        print('download_masterindex:  ' + str(year) + ':' + str(qtr) + ' | ' +
              'len() = {:,}'.format(len(masterindex)))

    return masterindex


class MasterIndexRecord:
    def __init__(self, line):
        self.err = False
        parts = line.split('|')
        if len(parts) == 5:
            self.cik = int(parts[0])
            self.name = parts[1]
            self.form = parts[2]
            self.filingdate = int(parts[3].replace('-', ''))
            self.path = parts[4]
        else:
            self.err = True
        return

#
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

# Replace unicode characters with their "normal" representations
# and identify item headers in 10-K forms
def Text_Normlization(text):
    text = unicodedata.normalize('NFKC', text)

    text = re.sub(r'\n|\r|\t', ' ', text)
    # Remove double spacing and backslashes
    text = re.sub(r'\s+', ' ', text)
    # Remove leading space
    text = text.strip()

    text = re.sub(re.compile("Items", re.IGNORECASE), "Item", text)
    text = re.sub(re.compile("PART I", re.IGNORECASE), "", text)
    text = re.sub(re.compile("ITEM III", re.IGNORECASE), "Item 3", text)
    text = re.sub(re.compile("ITEM II", re.IGNORECASE), "Item 2", text)
    text = re.sub(re.compile("Item I|Item l", re.IGNORECASE), "Item 1", text)

    text = re.sub(re.compile(":|\\*", re.IGNORECASE), "", text)
    text = re.sub('-', ' ', text)

    text = text.replace("ONE", "1")
    text = re.sub(re.compile("ONE", re.IGNORECASE), "1", text)
    text = re.sub(re.compile("TWO", re.IGNORECASE), "2", text)
    text = re.sub(re.compile("THREE", re.IGNORECASE), "3", text)

    text = re.sub(r'1\s{0,}\.', '1', text)
    text = re.sub(r'2\s{0,}\.', '2', text)
    text = re.sub(r'3\s{0,}\.', '3', text)
    return text


def Extract_Business_Desc(text_tree):
    # Return the longest passages that seems like the Business Descrp in a 10-K

    text = list(map(Text_Normlization, text_tree))

    # Remove empty lines and expand the business descriptions
    empty_line = re.compile(r"^\s*$", re.IGNORECASE)
    item_number = re.compile(r"^ITEM\s{0,}\d{0,}\s{0,}$|^ITEM\s{0,}1 AND 2\s{0,}$", re.IGNORECASE)
    # Remove empty lines
    empty_lines = []
    for m in range(0, len(text)):
        if empty_line.match(text[m]):
            empty_lines.append(m)

    for m in sorted(empty_lines, reverse=True):
        del text[m]

    # Concatenate the section headers divisions
    item_numbers = []
    for m in range(0, (len(text)-1)):
        if item_number.match(text[m]):
            item_numbers.append(m)

    for m in item_numbers:
        text[m+1] = text[m] + ' ' + text[m+1]

    # iterate through the elements to find the right text section
    startline = re.compile(r"^ITEM\s{0,}1\s{0,}\W{0,}\s{0,}BUSINESS\s{0,}\.{0,1}\s{0,}$|^ITEM\s{0,}1\s{0,}\W{0,}\s{0,}DESCRIPTION OF BUSINESS\s{0,}\.{0,1}\s{0,}$", re.IGNORECASE)
    endline = re.compile(r"^ITEM\s{0,}2\s{0,}\W{0,}\s{0,}PROPERTIES\s{0,}\.{0,1}\s{0,}$|^ITEM\s{0,}2\s{0,}\W{0,}\s{0,}DESCRIPTION OF PROPERTY\s{0,}\.{0,1}\s{0,}$|^ITEM\s{0,}2\s{0,}\W{0,}\s{0,}REAL ESTATE\s{0,}\.{0,1}\s{0,}$", re.IGNORECASE)
    startline_positions = []
    endline_positions = []
    for m in range(0, len(text)):
        if startline.match(text[m]):
            startline_positions.append(m)
        if endline.match(text[m]):
            endline_positions.append(m)

    # For the case that we can't find the regular expressions
    # as we would expect them, there must be some other pattern
    # of business descriptions
    if (len(startline_positions) == 0 & len(endline_positions) == 0):
        startline = re.compile(r"^ITEM\s{0,}1 AND 2\s{0,}\W{0,}\s{1,}BUSINESS AND PROPERTIES\s{0,}\.{0,1}\s{0,}$|^ITEM\s{0,}1 AND 2\s{0,}\W{0,}\s{1,}BUSINESS AND DESCRIPTION OF PROPERTY\s{0,}\.{0,1}\s{0,}$", re.IGNORECASE)
        endline = re.compile(r"^ITEM\s{0,}3s{0,}\W{0,}\s{1,}LEGAL PROCEEDINGS\s{0,}\.{0,1}\s{0,}$|^ITEM\s{0,}3s{0,}\W{0,}\s{1,}LEGAL MATTERS\s{0,}\.{0,1}\s{0,}$", re.IGNORECASE)
        for m in range(0, len(text)):
            if startline.match(text[m]):
                startline_positions.append(m)
            if endline.match(text[m]):
                endline_positions.append(m)


    if (min(len(startline_positions), len(endline_positions)) > 0):
        passages = []
        if (len(startline_positions) == len(endline_positions)):
            for i in range(0,len(startline_positions)):
                passages.append(' '.join(text[startline_positions[i]:endline_positions[i]]))
        else:
            # if the phrases don't have the same length, use the last mentioning:
            passages.append(' '.join(text[startline_positions[-1]:endline_positions[-1]]))

        for m in range(0,len(passages)):
            passages[m] = re.sub(r'\s{2,}', ' ', passages[m])

        return max(passages, key = len)
    else:
        return 'PARSINGERROR'
#
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

def Business_description_to_doc(masterindex_item):
    # Download url content to string text and extract the business section
    # Loop accounts for temporary server/ISP issues

    # Setup EDGAR URL and output file name
    _url = PARM_EDGARPREFIX + masterindex_item.path

    # Keep track of filings and identify duplicates
    fid = str(masterindex_item.cik) + str(masterindex_item.filingdate) + masterindex_item.form
    if fid in file_count:
        file_count[fid] += 1
    else:
        file_count[fid] = 1

    fname = (path + str(masterindex_item.filingdate) + '_' + masterindex_item.form.replace('/', '-') + '_' +
             masterindex_item.path.replace('/', '_'))
    fname_bd = fname.replace('.txt', '_BusinessDesc' + '_' + str(file_count[fid]) + '.txt')
    fname_raw = fname.replace('.txt', '_RawText' + '_' + str(file_count[fid]) + '.txt')
    fname_ft = fname.replace('.txt', '_FullText' + '_' + str(file_count[fid]) + '.txt')

    number_of_tries = 3
    sleep_time = 5
    time_out = 3

    status = False

    for i in range(1, number_of_tries + 1):
        try:
            response = requests.get(_url, headers=HEADER, timeout = time_out)
            if response.status_code/100 < 3:
              status = True
              break
        except Exception as exc:
            if i == 1:
                print('\n==>urlopen error in download_to_doc.py')
            print('  {0}. _url:  {1}'.format(i, _url))
            print('     Warning: {0}'.format(str(exc)))
            if '404' in str(exc):
                break
            print('     Retry in {0} seconds'.format(sleep_time))
            time.sleep(sleep_time)

    if status:
        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove HTML tags with get_text
            body = soup.body
            for tag in body.select('script'):
                tag.decompose()
            for tag in body.select('style'):
                tag.decompose()
            for tag in body.select('form'):
                tag.decompose()
            for tag in body.select('noscript'):
                tag.decompose()
            text_tree = [m for m in body.strings]

        except Exception as exc:
            print(exc)
            # If html parser fails, use lxml method to parse text (more stable and lenient)
            tree = html.fromstring(response.content.decode(response.encoding))
            text_tree_object =  tree.xpath("//text()[not(ancestor::script)][not(ancestor::style)][not(ancestor::noscript)][not(ancestor::form)]")
            text_tree = [str(x) for x in text_tree_object]


        # Write raw text result into output file
        with open(fname_raw, "w", encoding="utf-8") as f:
            f.write('\n'.join(text_tree))
        f.close()

        # Write full text result into output file
        full_text = list(map(Text_Normlization, text_tree))
        full_text = re.sub(r'\n|\r|\t', ' ', ' '.join(full_text))
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = full_text.strip()

        with open(fname_ft, "w", encoding="utf-8") as f:
            f.write(full_text)
        f.close()

        business_descr = Extract_Business_Desc(text_tree)
        if not business_descr == 'PARSINGERROR':

            # Write actual result into output file
            with open(fname_bd, "w", encoding="utf-8") as f:
                f.write(business_descr)
            f.close()

            return [masterindex_item.cik, masterindex_item.name, masterindex_item.form,
                    masterindex_item.filingdate, masterindex_item.path, file_count[fid], fname, full_text, business_descr, True]
        else:
            # if itteration is unsuccessful, return buffer text
            return  [masterindex_item.cik, masterindex_item.name, masterindex_item.form,
                     masterindex_item.filingdate, masterindex_item.path, file_count[fid], fname, full_text, '', "PARSINGERROR"]


    print('\n  ERROR:  Download failed for url: {0}'.format(_url))
    return [masterindex_item.cik, masterindex_item.name, masterindex_item.form,
            masterindex_item.filingdate, masterindex_item.path, file_count[fid], fname, '', '', "DOWNLOADINGERROR"]

#
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * +


# Download relevant masterindex
def Masterindex_iteratable_download(PARM_LOGFILE, 
                                    PARM_BGNYEAR, PARM_ENDYEAR, 
                                    PARM_BGNQTR, PARM_ENDQTR, 
                                    PARM_FORMS, PARM_CIK):
    # Download each year/quarter master.idx and save record for requested forms
    f_log = open(PARM_LOGFILE, 'w')
    n_qtr = 0

    masterindex = []
    for year in range(PARM_BGNYEAR, PARM_ENDYEAR + 1):
        for qtr in range(PARM_BGNQTR, PARM_ENDQTR + 1):

            masterindex_expand = download_masterindex(year, qtr, True)
            if masterindex_expand:
                masterindex_expand_filtered = list(filter(lambda x: x.form in PARM_FORMS and x.cik in PARM_CIK, masterindex_expand))
                masterindex.extend(masterindex_expand_filtered)
                n_qtr += 1

            # time.sleep(1)  # Space out requests
            print(str(year) + ':' + str(qtr) + ' -> {0:,}'.format(n_qtr) + ' downloads completed.')

            f_log.write('{0} | {1} | n_qtr = {2:>8,}\n'.
                        format(year, qtr, n_qtr))
            f_log.flush()

    print('{0:,} total forms downloaded.'.format(n_qtr))
    f_log.write('\n{0:,} total forms downloaded.'.format(n_qtr))

    return(masterindex)
#
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * +

def Download_forms(PARM_PATH, PARM_LOGFILE, PARM_BGNYEAR, 
                   PARM_ENDYEAR, PARM_BGNQTR, PARM_ENDQTR, 
                   PARM_FORMS, PARM_CIK):
    # Main Executions Routine

    # Setup output path and extract already scraped entries
    path = PARM_PATH

    # Output CSV files
    csv_result_name = 'Status_EDGAR_Scraping.csv'
    df_csv_result_name = 'Status_EDGAR_Scraping_df.csv'

    col_list = ["CIK", "NAME", "FORM", "FILINGDATE", "EDGAR_PATH",\
                "FILECOUNT", "FILE_PATH", 'Full_Text', 'Business_Description', "WORKED"]
    result_df = pd.DataFrame(columns = col_list)

    existing_document = []

    if not os.path.exists(path):
        os.makedirs(path)

        print('Path: {0} created and output file'.format(path))

        # Create Output file CSV file
        with open(path + '//' + csv_result_name, "w", encoding = 'utf-8') as f:
            writer = csv.DictWriter(
                    f, fieldnames=col_list)
            writer.writeheader()
        f.close()

    else:

        print('Path: {0} exists already => Extract already existing files'.format(path))

        existing_document = os.listdir(path)

    path = path + '//'


    # Collection of global variables that should live outside of the execution path
    def initializer(path_dir):
        global path
        global file_count
        # Define the result list as global so it can live independent of the path of the execution
        global result_list
        path = path_dir
        file_count = {}
        result_list = []

    masterindex = Masterindex_iteratable_download(PARM_LOGFILE, PARM_BGNYEAR,
                                                  PARM_ENDYEAR, PARM_BGNQTR,
                                                  PARM_ENDQTR, PARM_FORMS,
                                                  PARM_CIK)

    # Linear execution
    initializer(path_dir = path)

    for index_entry in masterindex:
        print('Scraping now file {0} for {1}, for the filing date {2}'.format(index_entry.form, index_entry.name, index_entry.filingdate))

        fpath = (str(index_entry.filingdate) + '_' + index_entry.form.replace('/', '-') + '_' + index_entry.path.replace('/', '_'))
        fpath = fpath.replace('.txt', '')

        if any(fpath in s for s in existing_document):
            print('\t file {0} for {1}, for the filing date {2} already in list => Extract Entries'.format(index_entry.form, index_entry.name, index_entry.filingdate))

            # Find files in already scraped text
            files = [s for s in existing_document if fpath in s]

            file_counts_list = [re.findall(r"_(\d+)\.txt$", s)[0] for s in files]
            file_counts_list = list(set(file_counts_list))

            for file_counts_listitem in file_counts_list:
                f_text = ''
                bd_text = ''
                for text_path in files:
                    if ('BusinessDesc' in text_path) and (re.findall(r"_(\d+)\.txt$", text_path)[0] == file_counts_listitem):
                        text_read = open(path + text_path, 'r', encoding = 'utf-8')
                        bd_text = text_read.read()

                    if ('FullText' in text_path) and (re.findall(r"_(\d+)\.txt$", text_path)[0] == file_counts_listitem):
                        text_read = open(path + text_path, 'r', encoding = 'utf-8')
                        f_text = text_read.read()

                        fid = str(index_entry.cik) + str(index_entry.filingdate) + index_entry.form
                        if fid in file_count:
                            file_count[fid] += 1
                        else:
                            file_count[fid] = 1

                # Adjust error message
                if bd_text != '':
                    error_message = True
                else:
                    if f_text != '':
                        error_message = "PARSINGERROR"
                    else:
                        error_message = "DOWNLOADINGERROR"

                # Add to result list
                append_item = [index_entry.cik, index_entry.name, index_entry.form,
                                    index_entry.filingdate, index_entry.path, file_counts_listitem, text_path,
                                    f_text, bd_text, error_message]
                result_list.append(append_item)
                result_df.loc[len(result_df)] = append_item

        else:
            append_item = Business_description_to_doc(index_entry)
            result_list.append(append_item)
            result_df.loc[len(result_df)] = append_item


    # Write the resulting now into a csv file
    print('End of Scraping, writing out now')
    result_df.to_csv(path_or_buf = path + df_csv_result_name, encoding = 'utf-8')

    with open(path + csv_result_name, "a", newline = '', encoding = 'utf-8') as f:
        writer = csv.writer(f)
        for status_result in result_list:
            writer.writerow(status_result)
    f.close()


    # Write the file count now into a csv file
    print('Write out file count now')
    with open(path + 'file_count_' + str(PARM_BGNYEAR) + '-' + str(PARM_ENDYEAR) + '.csv',\
              "w", newline = '', encoding = 'utf-8') as f:
        writer = csv.writer(f)
        for key, val in file_count.items():
            writer.writerow([key, val])
    f.close()

    return(result_df)


# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * +
# Helper function to extract the listed masterindex entries

def master_index_listing(PARM_PATH, PARM_LOGFILE,
                         PARM_BGNYEAR, PARM_ENDYEAR,
                         PARM_BGNQTR, PARM_ENDQTR,
                         PARM_FORMS, PARM_CIK):

    # Download Masterindex
    masterindex = Masterindex_iteratable_download(PARM_LOGFILE, PARM_BGNYEAR,
                                                  PARM_ENDYEAR, PARM_BGNQTR,
                                                  PARM_ENDQTR, PARM_FORMS,
                                                  PARM_CIK)

    # Set same function parameters as in main
    path = PARM_PATH
    file_count = {}

    # Create Output File
    col_list = ["CIK", "NAME", "FORM", "FILINGDATE", "EDGAR_PATH",\
                "FILECOUNT", "FILE_PATH"]
    master_index_list_df = pd.DataFrame(columns = col_list)

    for masterindex_item in masterindex:
        # Keep track of filings and identify duplicates
        fid = str(masterindex_item.cik) + str(masterindex_item.filingdate) + masterindex_item.form
        if fid in file_count:
            file_count[fid] += 1
        else:
            file_count[fid] = 1

        # Append index entry
        append_item = [masterindex_item.cik, masterindex_item.name,
                       masterindex_item.form, masterindex_item.filingdate,
                       masterindex_item.path, file_count[fid],
                       (path + '//' + str(masterindex_item.filingdate)
                        + '_' + masterindex_item.form.replace('/', '-')
                        + '_' + masterindex_item.path.replace('/', '_'))]
        master_index_list_df.loc[len(master_index_list_df)] = append_item

    # Save Output
    master_index_list_df.to_csv(path_or_buf = path + '//Masterindex_List.csv', encoding = 'utf-8')
    return(master_index_list_df)

# -----------------------
# User defined parameters
# -----------------------

# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * +
# Predefined SEC form strings

f_10K = ['10-K', '10-K405', '10KSB', '10-KSB', '10KSB40']
f_10KA = ['10-K/A', '10-K405/A', '10KSB/A', '10-KSB/A', '10KSB40/A']
f_10KT = ['10-KT', '10KT405', '10-KT/A', '10KT405/A']
f_10Q = ['10-Q', '10QSB', '10-QSB']
f_10QA = ['10-Q/A', '10QSB/A', '10-QSB/A']
f_10QT = ['10-QT', '10-QT/A']

# List of all 10-X related forms
f_10X = f_10K + f_10KA + f_10KT + f_10Q + f_10QA + f_10QT

# Regulation A+ related forms
f_1X = ['1-A', '1-A/A', '1-K', '1-SA', '1-U', '1-Z']
#
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * +


# EDGAR parameter
PARM_EDGARPREFIX = 'https://www.sec.gov/Archives/'


#***********************************************
# Main Routine
#***********************************************

def Download_Execution(home_directory, PARM_PATH, 
                       PARM_BGNYEAR, PARM_ENDYEAR, 
                       PARM_FORMS, PARM_CIK, 
                       PARM_BGNQTR=1, PARM_ENDQTR=4):
    '''
    METHOD: Main Routine for Execution of EDGAR Scraping
    INPUT:  home_directory = main directory where output should be created
            PARM_PATH = Output filepath for scraped EDGAR Documents,
            PARM_BGNYEAR = First year of scraping window,
            PARM_ENDYEAR = Last year of scraping window,
            PARM_BGNQTR = Beginning quarter of each scraping year,
            PARM_ENDQTR = End quarter of each scraping year,
            PARM_FORMS = EDGAR form type to be scraped,
            PARM_CIK = List of CIK codes to be scraped
    OUTPUT: Result DataFrame containing fulltext and Business Descriptions,
            Folder in PARM_PATH containing scraped text files from EDGAR with the name structure
            Filingdate_FormType_ItemID; ItemID consists of CIK-FiscalYear(two digits)-Sequential Count of Submitted File
    '''



    # Create Logfile path
    PARM_LOGFILE = (r'Log Files//' +
                r'EDGAR_Download_FORM-X_LogFile_' +
                str(PARM_BGNYEAR) + '-' + str(PARM_ENDYEAR) + '.txt')


    # Create Target Directory
    os.chdir(home_directory)
    try:
        os.makedirs(PARM_PATH)
    except FileExistsError:
        print('Directory not created.')

    try:
        os.makedirs('Log Files')
    except FileExistsError:
        print('Log Files Directory not created.')

    edgar_scraping_result = Download_forms(PARM_PATH, PARM_LOGFILE,
                                           PARM_BGNYEAR, PARM_ENDYEAR,
                                           PARM_BGNQTR, PARM_ENDQTR,
                                           PARM_FORMS, PARM_CIK)
    


    return(edgar_scraping_result)

########################################################################
# Main Executions
########################################################################
if __name__ == '__main__':
    
    # Sample execution for Apple:
    # https://www.sec.gov/edgar/browse/?CIK=0000320193
    
    home_directory = '/Users/dominikjurek/Library/CloudStorage/Dropbox/University/PhD Berkeley/Research/Alice Project/NLP Patent Classification/Alice NLP Python Code/Testing Github files/EDGAR_scraping'
    os.chdir(home_directory)
    
    Download_Execution(home_directory=os.getcwd(), 
                       PARM_PATH='EDGAR_scraping_for_Apple', 
                       PARM_BGNYEAR=2019, 
                       PARM_ENDYEAR=2022, 
                       PARM_FORMS=f_10X, 
                       PARM_CIK=[320193], 
                       PARM_BGNQTR=1, 
                       PARM_ENDQTR=4)

#_url = 'https://www.sec.gov/Archives/edgar/data/1074828/0001199835-08-000024.txt'
#test_url = 'https://www.sec.gov/Archives/edgar/data/1000180/0001000180-10-000008.txt'
#response = requests.get(_url)




