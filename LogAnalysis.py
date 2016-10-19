import sys, re, glob
import pandas as pd
from pprint import pprint

class LogAnalysis:
    def __init__(self, log_file, test_cases):
        self.log_file = log_file
        self.test_cases = test_cases


    def score(self, app, test):
        app_split = set(app.split('/'))
        test_split = set(test.split('/'))
        return len(app_split.intersection(test_split)) / len(app_split)

    def format_log(self, log_file_name):
        with open(log_file_name) as log_file:
            log_text = log_file.read()

        log_lines = re.findall(r'((^\d+-\d+-\d+.+0m$)|(^\d+-\d+-\d+.+error:.+$))', log_text, re.M)
        logs = [line[0] for line in log_lines]

        log_parsed = []
        for line in logs:
            if re.search(r'error:', line) is not None:
                date = re.search(r'\d+-\d+-\d+', line).group(0),
                time = re.search(r'\d{2}:\d{2}:\d{2}', line).group(0),
                req_type = 'ERROR',
                request = 'ERROR',
                resp_type = re.search(r'(info)|(error)', line).group(0),
                resp_code = 'ERROR'
            else:
                date = re.search(r'\d+-\d+-\d+', line).group(0),

                time = re.search(r'\d{2}:\d{2}:\d{2}', line).group(0),

                if re.search(r'(GET)|(POST)', line) is None:
                    req_type = ''
                else:
                    req_type = re.search(r'(GET)|(POST)', line).group(0),

                if re.search(r'(/\S+)+', line) is None:
                    request = '/'
                else:
                    request = re.search(r'(/\S+)+', line).group(0),

                resp_type = re.search(r'(info)|(error)', line).group(0),

                if re.search(r'\[\d+m\d{3}', line) is None:
                    resp_code = ''
                else:
                    resp_code = re.search(r'\[\d+m\d{3}', line).group(0)[-3:]

            log_parsed.append({
                'date': date[0],
                'time': time[0],
                'req_type': re.sub(r'[(,)\']', '', str(req_type)),
                'request': re.sub(r'[(,)\']', '', str(request)),
                'resp_type': re.sub(r'[(,)\']', '', str(resp_type)),
                'resp_code': resp_code
            })
        return log_parsed

    def get_test_sequence(self):
        app_log = self.format_log(self.log_file)
        app_log_len = len(app_log)

        test_logs = []
        for file in self.test_cases:
            test_logs.append(self.format_log(file))

        output = [None] * app_log_len
        test_num = 1
        for test_log in test_logs:
            i = 0
            test_len = len(test_log)
            test_name = 'TC' + str(test_num)
            while i <= app_log_len - test_len:
                match = 0
                for app, test in zip(app_log[i:], test_log):
                    # -----------to find exact match-------------
                    # if app['request'] != test['request']:
                    if self.score(app['request'], test['request']) < 0.7:
                        if match == 0:
                            i += 1
                            break
                        elif app['request'] == 'ERROR' and i < app_log_len - match and not any(output[i:i + match]):
                            if match >= int(test_len * 0.5):
                                output[i:i + match] = [test_name for aa in output[i:i + match]]
                            else:
                                output[i:i + match] = ['Unknown' for aa in output[i:i + match]]
                            output[i + match + 1] = app['request']
                            i += (match + 2)
                            break
                        else:
                            i += match
                            break
                    else:
                        match += 1
                if match == test_len:
                    output[i:i + match] = [test_name for aa in output[i:i + match]]
                    i += (match + 1)
            test_num += 1

        for i in range(len(output)):
            if output[i] is None: output[i] = 'ERROR'

        out_shrunk = []
        match = ''
        for line in output:
            if line != match:
                out_shrunk.append(line)
                match = line

        pd.DataFrame(output).to_csv('./output.csv', index=False, header=False)
        pd.DataFrame(out_shrunk).to_csv('./output_shrunk.csv', index=False, header=False)

        # print('Length: ' + str(len(output)) + '\n')
        # print('--------------------------------------\n\n')
        # pprint(out_shrunk)

        return output, out_shrunk

    def extract_errors(self):
        with open(self.log_file) as f:
            log_lines = f.read()

        errors = re.findall(r'(^\d+-\d+-\d+.+error:.+$)|((Error:.+$)|(.+at\s.+$))', log_lines, re.M)

        errors_parsed = []
        i = -1
        for error in errors:
            if re.search(r'^\d+-\d+-\d+', error[0]) is not None:
                errors_parsed.append(error[0])
                i += 1
            else:
                errors_parsed[i] = errors_parsed[i] + error[0] + error[1] + error[2]

        error_abstract = []
        key = 1
        for error_parsed in errors_parsed:
            date = re.search(r'\d+-\d+-\d+', error_parsed).group(0)
            time = re.search(r'\d{2}:\d{2}:\d{2}', error_parsed).group(0)
            error_message = re.sub(r'Error:.+', '',
                                   error_parsed[
                                   error_parsed.find('Error:') + len('Error:'):error_parsed.find('    at ')])
            error_type = re.sub('Error:', '', re.search(r'[A-Za-z]*Error:', error_parsed).group(0))
            if error_type == '':
                error_type = 'Unknown'
            sources = re.findall(r'at\s.+\s\S+\s', error_parsed, re.M)
            sources = str(sources).split(' at')

            error_source = '\n'.join([re.sub(r'^\[\'at', '', source) for source in sources if
                                      re.search(r'(\\lib\\)|(\\\S+_modules\\)', source) is None and re.search(
                                          r'\S+\\\S+',
                                          source) is not None])

            error_abstract.append({
                'key': key,
                'date': date,
                'time': time,
                'error_message': error_message,
                'error_type': error_type,
                'error_source': error_source
            })
            key += 1

        errors_split = []
        for error_block in error_abstract:
            error_sources = error_block['error_source'].splitlines()
            for error_source in error_sources:
                line_col = re.search(r'\d+:\d+', error_source).group(0)
                error_source = re.sub(r':\d+:\d+', '', error_source)
                errors_split.append({
                    'key': error_block['key'],
                    'date': error_block['date'],
                    'time': error_block['time'],
                    'error_message': error_block['error_message'],
                    'error_type': error_block['error_type'],
                    'error_source': error_source,
                    'line:col': line_col
                })

        pd.DataFrame(error_abstract).to_csv('./error_details.csv', index=False)
        pd.DataFrame(errors_split).to_csv('./error_details_split.csv', index=False)

        return error_abstract, errors_split

if __name__ == '__main__':
    # log_analysis = LogAnalysis('./app3.log', glob.glob('./*.txt'))
    log_analysis = LogAnalysis(sys.argv[1], glob.glob('./*.' + sys.argv[2]))
    out_full, out = log_analysis.get_test_sequence()
    print('Test Case & Error Pattern:')
    print('--------------------------------------\n')
    pprint(out)
    print('\n\n')
    print('ERROR DETAILS: ')
    print('--------------------------------------\n\n')
    errors, errors_split = log_analysis.extract_errors()
    pprint(list(enumerate(errors)))
    # print('\n--------------------------------------\n\n')
    # pprint(errors_split)