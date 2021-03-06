from __future__ import division
import os
import zipfile
import wget
import shutil
import logging
import logging.config
import numpy as np

PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(PROJECT_ROOT_DIR, 'data')
TMP_FOLDER = os.path.join(PROJECT_ROOT_DIR, 'tmp')

# MovieLens 1M
MOVIELENS1M_DATA_FOLDER = os.path.join(DATA_FOLDER, 'MovieLens1M')
MOVIELENS1M_URL = 'http://files.grouplens.org/datasets/movielens/ml-1m.zip'

LOG_CONFIG = os.path.join(os.path.dirname(__file__), 'logs/logging.conf')
LOG_OUT = os.path.join(os.path.dirname(__file__), 'logs/output.log')

logger = None


def initialize_logging(name):
    """ Initializes logging with the default configuration and the
    output where to store the logs. Set to None to disable storing into file
     :param name: Name of the logger to initialize """
    logging.config.fileConfig(LOG_CONFIG, defaults={'logfilename': LOG_OUT})
    logger = logging.getLogger(name)
    logger.propagate = False
    return logger


def get_logger(name='cbr'):
    """ Returns logger instance """
    global logger
    if logger is None:
        logger = initialize_logging(name)
    return logger


logger = get_logger()


## Utility functions


def check_download_data(url=MOVIELENS1M_URL, output=MOVIELENS1M_DATA_FOLDER):
    """ Download MovieLens into the given folder if does not exists"""
    if not os.path.isdir(output):

        logger.info("Downloading data from %s into %s ..." % (url, output))

        # Download into temporary file
        tmp_path = wget.download(url, out=TMP_FOLDER)

        create_dir(output)

        # Extract content
        with open(tmp_path) as f:
            zipped = zipfile.ZipFile(f)

            for name in zipped.namelist():
                # Get only files
                filename = os.path.basename(name)
                # skip directories
                if not filename:
                    continue

                # Copy into data folder
                with zipped.open(name) as src:
                    with open(os.path.join(output, filename), 'wb') as dst:
                        shutil.copyfileobj(src, dst)

        # Remove tmp file
        os.remove(tmp_path)


def create_dir(folder):
    """ Creates folder if it does not exists """
    if not os.path.isdir(folder):
        os.makedirs(folder)


def split_data(num, train_ratio):
    """ Randomly splits indices [0, num] into training and test """
    train = int(num * train_ratio)
    perm = np.random.permutation(num)
    return perm[:train], perm[train:]


def check_ratio(name, value):
    """ Checks whether input is in interval [0, 1]. Otherwise raises exception"""
    if value < 0 or value > 1:
        raise ValueError("Parameter %s must be in interval [0,1] but is %f" % value)


def jaccard_similarity(labels1, labels2):
    """ Returns the Jaccard index between two vectors of labels"""
    lab_set1, lab_set2 = set(labels1), set(labels2)
    return len(lab_set1.intersection(lab_set2)) / len(set(lab_set1).union(lab_set2))


def improved_jaccard_similarity(list_1, list_2):
    """ Returns the Jaccard index between two sets
    Source: http://love-python.blogspot.com.es/2012/07/python-code-to-compute-jaccard-index.html """
    set_1 = set(list_1)
    set_2 = set(list_2)
    n = len(set_1.intersection(set_2))
    return n / float(len(set_1) + len(set_2) - n)


def pearson_correlation(items1, items2, mean1, mean2):
    """ Returns the Pearson correlation between the two input elements """
    num = sum((items1 - mean1) * (items2 - mean2))
    den = np.sqrt(sum(np.square(items1 - mean1))) * np.sqrt(sum(np.square(items2 - mean2)))
    return num / den if den != 0 else 0.0


def save_list(inp, path):
    """ Saves input list into the given path """
    with open(path, 'w') as f:
        for elem in inp:
            f.write(str(elem) + '\n')
