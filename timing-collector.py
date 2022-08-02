#!/usr/bin/env python

import requests
import random
import time
import sys

from utils.progress import progress
from utils.os_utils import (setCPUAffinity, setLowLatency,
                            setPowersave, setTCPTimestamps)
from CodernityDB.database import Database
from CodernityDB.index import IndexConflict

VALID_TOKEN_START = '224a93060c0dd4fb931d05083b4cb7b6a'
VALID_TOKEN_GUESS = '8c27df8'

TOTAL_LENGTH = len(VALID_TOKEN_START) + len(VALID_TOKEN_GUESS)
MISSING_CHAR_LENGTH = len(VALID_TOKEN_GUESS)

PADDING_CHAR = '0'
WARM_UP_COUNT = 100

URL = 'http://127.0.0.1:8000/users/'
NUM_SAMPLES = 10000
OUTPUT_DB = 'token-timing.db'

TEST_NAME = sys.argv[1]


def generate_test_token(known_valid, test_char, missing_chars):
    return (known_valid +
            test_char +
            PADDING_CHAR * (missing_chars - 1))


def send_with_naive_timing(session, url, token):
    # Prepare the request this way to avoid the auto-added User-Agent and Accept
    # headers.
    #
    # TODO: What happens if I want to send data? Do I need to add the
    #       Content-Type header manually?
    req = requests.Request(
        'GET',
        url,
        headers={
            'Authorization': f'Token {token}',
            'Accept-Encoding': 'identity',
        },
    )

    prepared_request = req.prepare()

    response = session.send(prepared_request,
                            allow_redirects=False,
                            verify=False)
    naive_time = response.elapsed.microseconds

    return response, naive_time


def send_requests(db, known_valid, test_case_1, test_case_2, missing_chars):
    """
    :param db: The database where samples are stored
    :param known_valid: The known valid characters
    :param test_case_1: One character to test (test case 1)
    :param test_case_2: One character to test (test case 2)
    :param missing_chars: The total number of chars of the API key
    :return: None. All is stored in the DB
    """
    session = requests.Session()

    http_adapter = requests.adapters.HTTPAdapter(max_retries=3)

    session.mount('http://', http_adapter)
    session.mount('https://', http_adapter)

    token_test_case_1 = generate_test_token(known_valid,
                                            test_case_1,
                                            missing_chars)

    token_test_case_2 = generate_test_token(known_valid,
                                            test_case_2,
                                            missing_chars)

    print(f'Collecting {NUM_SAMPLES} samples for:' * 2)
    print(f' - {token_test_case_1}')
    print(f' - {token_test_case_2}')
    print('')
    print(f'Test name: {TEST_NAME}')

    for i in xrange(NUM_SAMPLES):

        #
        # What I'm trying to do here is to get timings in pairs.
        # https://github.com/andresriancho/django-rest-framework-timing/issues/5
        #
        tmp_results = {}

        # Sending the HTTP requests in different order during sample capture is
        # something recommended by Paul McMillan and Sebastian Schinzel, they
        # recommend it because it might break some caches
        shuffled_token_tests = [(0, token_test_case_1),
                                (1, token_test_case_2)]
        random.shuffle(shuffled_token_tests)

        for j, token in shuffled_token_tests:
            response, naive_time = send_with_naive_timing(session, URL, token)
            tmp_results[j] = (response, naive_time, token)

        data = {'test_name': TEST_NAME,
                'capture_timestamp': time.time()}

        for j, (response, naive_time, token) in enumerate(tmp_results.values()):
            data |= {
                f'x_runtime_{j}': response.headers['X-Runtime'],
                f'userspace_rtt_microseconds_{j}': naive_time,
                f'token_{j}': token,
            }


        db.insert(data)

        if i % (NUM_SAMPLES / 1000) == 0:
            progress(i, NUM_SAMPLES)


def warm_up(valid_token_start, success, fail, missing_char_length):
    """
    Use different TCP/IP connections to warm up all the threads
    """
    fail_token = generate_test_token(valid_token_start, fail,
                                     missing_char_length)
    success_token = generate_test_token(VALID_TOKEN_START, success,
                                        missing_char_length)

    for token in (fail_token, success_token):
        for _ in xrange(WARM_UP_COUNT):
            # TODO: What happens if I want to send data? Do I need to add the
            #       Content-Type header manually?
            req = requests.Request(
                'GET',
                URL,
                headers={
                    'Authorization': f'Token {token}',
                    'Accept-Encoding': 'identity',
                },
            )

            prepared_request = req.prepare()

            # Use different sessions/TCP connections to potentially warm up
            # more/different caches
            session = requests.Session()
            session.send(prepared_request,
                         allow_redirects=False,
                         verify=False)


def init_db():
    db = Database(OUTPUT_DB)

    try:
        db.create()
    except IndexConflict:
        db.open()

    return db


def init_os_settings():
    setCPUAffinity()
    setLowLatency(True)
    setPowersave(False)
    return setTCPTimestamps(True)


def clear_os_settings(tcpts_previous):
    setLowLatency(False)
    setPowersave(True)
    setTCPTimestamps(tcpts_previous)


if __name__ == '__main__':
    FAIL_1 = '7'
    FAIL_2 = '0'
    FAIL_3 = '1'
    SUCCESS = '8'

    FAIL_TEST = FAIL_1
    SUCCESS_TEST = SUCCESS

    tcpts_previous = False

    try:
        tcpts_previous = init_os_settings()
        db = init_db()

        warm_up(VALID_TOKEN_START, SUCCESS_TEST, FAIL_TEST, MISSING_CHAR_LENGTH)

        send_requests(db, VALID_TOKEN_START,
                      SUCCESS_TEST, FAIL_TEST,
                      MISSING_CHAR_LENGTH)
    except KeyboardInterrupt:
        print('')
        print('User pressed Ctrl+C.')
    finally:
        clear_os_settings(tcpts_previous)