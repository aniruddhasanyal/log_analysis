import re
import pandas as pd

with open('./app.log') as f:
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
                           error_parsed[error_parsed.find('Error:') + len('Error:'):error_parsed.find('    at ')])
    error_type = re.sub('Error:', '', re.search(r'[A-Za-z]*Error:', error_parsed).group(0))
    if error_type == '':
        error_type = 'Unknown'
    sources = re.findall(r'at\s.+\s\S+\s', error_parsed, re.M)
    sources = str(sources).split(' at')

    error_source = '\n'.join([re.sub(r'^\[\'at', '', source) for source in sources if
                              re.search(r'(\\lib\\)|(\\\S+_modules\\)', source) is None and re.search(r'\S+\\\S+',
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
