"""
@author: istiklal
"""
import logging

# import networkx as nx
# import matplotlib.pyplot as plt
# from PIL import Image
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger('commons')


def block_without_chart(center_title, svg_html_id,
                        first_line_name="", fist_line_value="", second_line_name="", second_line_value=""):
    """
    Use to create a similar block with chart blocks without chart as svg
    """
    if first_line_name == "" and fist_line_value == "":
        sep1 = ""
    else:
        sep1 = ":"

    if second_line_name == "" and second_line_value == "":
        sep2 = ""
    else:
        sep2 = ":"

    _graph = (
        f"""<svg class="graph chart" width="80" height="70%" viewbox="0 0 64 32" name="donut_chart" id="{svg_html_id}">
                 <circle name="CenterDisc" r="20%" cx="50%" cy="50%" style="stroke-width: 32; fill:white; stroke: grey;"></circle>
                 <circle name="CenterDisc" r="20%" cx="50%" cy="50%" style="stroke-width: 30; fill:white; stroke: white;"></circle>
                 <text fill="black" font-size="10" x="50%" y="50%" alignment-baseline="central" text-anchor="middle">{center_title} 
                 <small><br>{first_line_name} {sep1} {fist_line_value}<br>{second_line_name} {sep2} {second_line_value}</small></text>
                 </svg>""")

    return _graph


def triple_donut_chart(center_title, svg_html_id,
                       red_circle_name="RED", orange_circle_name="ORANGE", green_circle_name="GREEN",
                       red_circle_value=0, orange_circle_value=0, green_circle_value=0):
    """
    Use to create simple svg based donut charts with three arc. Red arc, orange arc and green arc as svg
    """

    _total = red_circle_value + orange_circle_value + green_circle_value
    if _total != 0:
        _red_per = (red_circle_value * 100) / _total
        _orange_per = (orange_circle_value * 100) / _total
        _green_per = (green_circle_value * 100) / _total
    else:
        _red_per, _orange_per, _green_per = 0, 0, 0

    if center_title == "":
        center_title = _total

    _graph = (f"""<svg class="graph chart" width="80" height="70%" viewbox="0 0 64 32" name="donut_chart" id="{svg_html_id}">
            <circle name="CenterDisc" r="20%" cx="50%" cy="50%" style="stroke-width: 25; fill:white; stroke: grey;"></circle>
            <circle name="RedBar" r="25%" cx="50%" cy="50%" style="stroke-width: 32; stroke-dasharray: {_red_per} 100; stroke: red; fill: none;"></circle>
            <circle name="OrangeBar" r="25%" cx="50%" cy="50%" style="stroke-width: 32;stroke-dasharray: {_orange_per} 100; stroke-dashoffset: {-_red_per}; stroke: orange;fill: none;"></circle>
            <circle name="GreenBar" r="25%" cx="50%" cy="50%" style="stroke-width: 32;stroke-dasharray: {_green_per} 100; stroke-dashoffset: {-(_red_per +_orange_per)}; stroke: green;fill: none;"></circle>
            <circle name="CenterDisc" r="20%" cx="50%" cy="50%" style="stroke-width: 20; fill:white; stroke: white;"></circle>
            <text fill="black" font-size="10" x="50%" y="50%" alignment-baseline="central" text-anchor="middle">{center_title} 
            <small><br>{red_circle_name} : {red_circle_value}<br>{orange_circle_name} : {orange_circle_value}<br>{green_circle_name} : {green_circle_value}</small></text>
            </svg>""")

    return _graph


def double_donut_chart(center_title, svg_html_id,
                       red_circle_name="RED", green_circle_name="GREEN",
                       red_circle_value=0, green_circle_value=0):
    """
    Use to create simple svg based donut charts with two arc. Red arc and green arc as svg
    """

    _total = red_circle_value + green_circle_value
    if _total != 0:
        _red_per = (red_circle_value * 100) / _total
        _green_per = (green_circle_value * 100) / _total
    else:
        _red_per, _green_per = 0, 0

    if center_title == "":
        center_title = _total

    _graph = (f"""<svg class="graph chart" width="80" height="70%" viewbox="0 0 64 32" name="donut_chart" id="{svg_html_id}">
             <circle name="CenterDisc" r="20%" cx="50%" cy="50%" style="stroke-width: 25;fill: white;stroke: grey;"></circle>
             <circle name="RedBar" r="25%" cx="50%" cy="50%" style="stroke-width: 32; stroke-dasharray: {_red_per} 100; stroke: red; fill: none;"></circle>
             <circle name="GreenBar" r="25%" cx="50%" cy="50%" style="stroke-width: 32;stroke-dasharray: {_green_per} 100; stroke-dashoffset: {-_red_per}; stroke: green;fill: none;"></circle>
             <circle name="CenterDisc" r="20%" cx="50%" cy="50%" style="stroke-width: 20;fill: white;stroke: white;"></circle>
             <text fill="black" font-size="10" x="50%" y="50%" alignment-baseline="central" text-anchor="middle">{center_title} 
             <small><br>{green_circle_name} : {green_circle_value}<br>{red_circle_name} : {red_circle_value}</small></text>
             </svg>""")

    return _graph


def report_main_grid(_object_dict):
    """
    Use to generate an report detail screen form the json data of report_format column as html codes
    """

    _v = ""
    for key, value in _object_dict.items():
        _v += f'<div class="row justify-content-center titles">{key}</div><div class="row">'
        for attr in value["attr_list"]:
            _v += f'<div class="col-sm-12 col-md-4 col-lg-3 frames"><div class="row justify-content-center">{attr}</div>'
            for obj in value["object_list"]:
                try:
                    _elm = getattr(obj, attr)
                    if _elm is None:
                        _elm = "No match"
                except ObjectDoesNotExist:
                    attr = f"{attr}_id"
                    _elm = getattr(obj, attr)
                    if _elm is None:
                        _elm = "No match"
                except Exception as err:
                    _elm = "-"
                    logger.exception(f"report_main_grid encountered an error like : {err}")
                _v += f'<span>{ str(_elm) }</span><br />'
            _v += '</div>'
        _v += '</div>'
    # logger.debug(f'generated html codes : {_v}')

    return _v


# def save_plot_as_image(graph_dict, map_id, show=False):
#
#     # with Image.open(os.path.join(BASE_DIR, 'static/rcChart/chart.png'), "w") as pic:
#     #     outer_plt.savefig(pic)
#
#     nx.draw(nx.readwrite.json_graph.adjacency_graph(graph_dict), with_labels=True)
#     plt.savefig(os.path.join(BASE_DIR, 'static/rcChart/chart.png'))
#
#     # if show:
#     #     plt.show()


help_psqlDateTimeFormats = [('Pattern', 'Description'),
                            ('HH', 'hour of day (01-12)'),
                            ('HH12', 'hour of day (01-12)'),
                            ('HH24', 'hour of day (00-23)'),
                            ('MI', 'minute (00-59)'),
                            ('SS', 'second (00-59)'),
                            ('MS', 'millisecond (000-999)'),
                            ('US', 'microsecond (000000-999999)'),
                            ('SSSS', 'seconds past midnight (0-86399)'),
                            ('AM, am, PM or pm', 'meridiem indicator (without periods)'),
                            ('A.M., a.m., P.M. or p.m.', 'meridiem indicator (with periods)'),
                            ('Y,YYY', 'year (4 or more digits) with comma'),
                            ('YYYY', 'year (4 or more digits)'),
                            ('YYY', 'last 3 digits of year'),
                            ('YY', 'last 2 digits of year'),
                            ('Y', 'last digit of year'),
                            ('IYYY', 'ISO 8601 week-numbering year (4 or more digits)'),
                            ('IYY', 'last 3 digits of ISO 8601 week-numbering year'),
                            ('IY', 'last 2 digits of ISO 8601 week-numbering year'),
                            ('I', 'last digit of ISO 8601 week-numbering year'),
                            ('BC, bc, AD or ad', 'era indicator (without periods)'),
                            ('B.C., b.c., A.D. or a.d.', 'era indicator (with periods)'),
                            ('MONTH', 'full upper case month name (blank-padded to 9 chars)'),
                            ('Month', 'full capitalized month name (blank-padded to 9 chars)'),
                            ('month', 'full lower case month name (blank-padded to 9 chars)'),
                            ('MON', 'abbreviated upper case month name (3 chars in English, localized lengths vary)'),
                            ('Mon', 'abbreviated capitalized month name (3 chars in English, localized lengths vary)'),
                            ('mon', 'abbreviated lower case month name (3 chars in English, localized lengths vary)'),
                            ('MM', 'month number (01-12)'),
                            ('DAY', 'full upper case day name (blank-padded to 9 chars)'),
                            ('Day', 'full capitalized day name (blank-padded to 9 chars)'),
                            ('day', 'full lower case day name (blank-padded to 9 chars)'),
                            ('DY', 'abbreviated upper case day name (3 chars in English, localized lengths vary)'),
                            ('Dy', 'abbreviated capitalized day name (3 chars in English, localized lengths vary)'),
                            ('dy', 'abbreviated lower case day name (3 chars in English, localized lengths vary)'),
                            ('DDD', 'day of year (001-366)'),
                            ('IDDD', 'day of ISO 8601 week-numbering year (001-371; day 1 of the year is Monday of the first ISO week)'),
                            ('DD', 'day of month (01-31)'),
                            ('D', 'day of the week, Sunday (1) to Saturday (7)'),
                            ('ID', 'ISO 8601 day of the week, Monday (1) to Sunday (7)'),
                            ('W', 'week of month (1-5) (the first week starts on the first day of the month)'),
                            ('WW', 'week number of year (1-53) (the first week starts on the first day of the year)'),
                            ('IW', 'week number of ISO 8601 week-numbering year (01-53; the first Thursday of the year is in week 1)'),
                            ('CC', 'century (2 digits) (the twenty-first century starts on 2001-01-01)'),
                            ('J', 'Julian Day (days since November 24, 4714 BC at midnight)'),
                            ('Q', 'quarter (ignored by to_date and to_timestamp)'),
                            ('RM', 'month in upper case Roman numerals (I-XII; I=January)'),
                            ('rm', 'month in lower case Roman numerals (i-xii; i=January)'),
                            ('TZ', 'upper case time-zone name'),
                            ('tz', 'lower case time-zone name')]

help_psqlStringOps = [('Functions', 'Return Type', 'Description', 'Example', 'Result'),
                      ('string || string', 'text', 'String concatenation', "Post' || 'greSQL'", 'PostgreSQL'),
                      ('string || non-string or non-string || string', 'text', 'String concatenation with one non-string input', "Value: ' || 42", 'Value: 42'),
                      ('bit_length(string)', 'int', 'Number of bits in string', "bit_length('jose')", '32'),
                      ('char_length(string) or character_length(string)', 'int', 'Number of characters in string', "char_length('jose')", '4'),
                      ('lower(string)', 'text', 'Convert string to lower case', "lower('TOM')", 'tom'),
                      ('octet_length(string)', 'int', 'Number of bytes in string', "octet_length('jose')", '4'),
                      ('overlay(string placing string from int [for int])', 'text', 'Replace substring', "overlay('Txxxxas' placing 'hom' from 2 for 4)", 'Thomas'),
                      ('position(substring in string)', 'int', 'Location of specified substring', "position('om' in 'Thomas')", '3'),
                      ('substring(string [from int] [for int])', 'text', 'Extract substring', "substring('Thomas' from 2 for 3)", 'hom'),
                      ('substring(string from pattern)', 'text', 'Extract substring matching POSIX regular expression. See Section 9.7 for more information on pattern matching.', "substring('Thomas' from '...$')", 'mas'),
                      ('substring(string from pattern for escape)', 'text', 'Extract substring matching SQL regular expression. See Section 9.7 for more information on pattern matching.', 'substring(\'Thomas\' from \'%#"o_a#"_\' for \'#\')', 'oma'),
                      ('trim([leading | trailing | both] [characters] from string)', 'text', 'Remove the longest string containing only the characters (a space by default) from the start/end/both ends of the string', "trim(both 'x' from 'xTomxx')", 'Tom'),
                      ('upper(string)', 'text', 'Convert string to upper case', "upper('tom')", 'TOM'),
                      ('ascii(string)', 'int', 'ASCII code of the first character of the argument. For UTF8 returns the Unicode code point of the character. For other multibyte encodings, the argument must be an ASCII character.', "ascii('x')", '120'),
                      ('btrim(string\xa0text\xa0[,\xa0characters\xa0text])', 'text', 'Remove the longest string consisting only of characters in characters (a space by default) from the start and end of string', "btrim('xyxtrimyyx', 'xy')", 'trim'),
                      ('chr(int)', 'text', 'Character with the given code. For UTF8 the argument is treated as a Unicode code point. For other multibyte encodings the argument must designate an ASCII character. The NULL (0) character is not allowed because text data types cannot store such bytes.', 'chr(65)', 'A'),
                      ("concat(str\xa0'any'\xa0[,\xa0str\xa0'any'\xa0[, ...] ])", 'text', 'Concatenate all arguments. NULL arguments are ignored.', "concat('abcde', 2, NULL, 22)", 'abcde222'),
                      ("concat_ws(sep\xa0text,\xa0str\xa0'any'\xa0[,\xa0str\xa0'any'\xa0[, ...] ])", 'text', 'Concatenate all but first arguments with separators. The first parameter is used as a separator. NULL arguments are ignored.', "concat_ws(',', 'abcde', 2, NULL, 22)", 'abcde,2,22'),
                      ('convert(string\xa0bytea,\xa0src_encoding\xa0name,\xa0dest_encoding\xa0name)', 'bytea', 'Convert string to dest_encoding. The original encoding is specified by src_encoding. The string must be valid in this encoding. Conversions can be defined by CREATE CONVERSION. Also there are some predefined conversions.', "convert('text_in_utf8', 'UTF8', 'LATIN1')", 'text_in_utf8\xa0represented in Latin-1 encoding (ISO 8859-1)'),
                      ('convert_from(string\xa0bytea,\xa0src_encoding\xa0name)', 'text', 'Convert string to the database encoding. The original encoding is specified by src_encoding. The string must be valid in this encoding.', "convert_from('text_in_utf8', 'UTF8')", 'text_in_utf8\xa0represented in the current database encoding'),
                      ('convert_to(string\xa0text,\xa0dest_encoding\xa0name)', 'bytea', 'Convert string to dest_encoding.', "convert_to('some text', 'UTF8')", 'some text\xa0represented in the UTF8 encoding'),
                      ('decode(string\xa0text,\xa0format\xa0text)', 'bytea', 'Decode binary data from textual representation in string. Options for format are same as in encode.', "decode('MTIzAAE=', 'base64')", '132330001'),
                      ('encode(data\xa0bytea,\xa0format\xa0text)', 'text', 'Encode binary data into a textual representation. Supported formats are: base64, hex, escape. escape converts zero bytes and high-bit-set bytes to octal sequences (\nnn) and doubles backslashes.', "encode(E'123\\000\\001', 'base64')", 'MTIzAAE='),
                      ("format(formatstr\xa0text\xa0[,\xa0str\xa0'any'\xa0[, ...] ])", 'text', 'Format a string. This function is similar to the C function sprintf ; but only the following conversion specifications are recognized: %s interpolates the corresponding argument as a string; %I escapes its argument as an SQL identifier; %L escapes its argument as an SQL literal; %% outputs a literal %. A conversion can reference an explicit parameter position by preceding the conversion specifier with n$, where n is the argument position.', "format('Hello %s, %1$s', 'World')", 'Hello World, World'),
                      ('initcap(string)', 'text', 'Convert the first letter of each word to upper case and the rest to lower case. Words are sequences of alphanumeric characters separated by non-alphanumeric characters.', "initcap('hi THOMAS')", 'Hi Thomas'),
                      ('left(str\xa0text,\xa0n\xa0int)', 'text', 'Return first n characters in the string. When n is negative, return all but last |n| characters.', "left('abcde', 2)", 'ab'),
                      ('length(string)', 'int', 'Number of characters in string', "length('jose')", '4'),
                      ('length(string\xa0bytea,\xa0encoding\xa0name\xa0)', 'int', 'Number of characters in string in the given encoding. The string must be valid in this encoding.', "length('jose', 'UTF8')", '4'),
                      ('lpad(string\xa0text,\xa0length\xa0int\xa0[,\xa0fill\xa0text])', 'text', 'Fill up the string to length length by prepending the characters fill (a space by default). If the string is already longer than length then it is truncated (on the right).', "lpad('hi', 5, 'xy')", 'xyxhi'),
                      ('ltrim(string\xa0text\xa0[,\xa0characters\xa0text])', 'text', 'Remove the longest string containing only characters from characters (a space by default) from the start of string', "ltrim('zzzytrim', 'xyz')", 'trim'),
                      ('md5(string)', 'text', 'Calculates the MD5 hash of string, returning the result in hexadecimal', "md5('abc')", '900150983cd24fb0 d6963f7d28e17f72'),
                      ('pg_client_encoding()', 'name', 'Current client encoding name', 'pg_client_encoding()', 'SQL_ASCII'),
                      ('quote_ident(string\xa0text)', 'text', 'Return the given string suitably quoted to be used as an identifier in an SQL statement string. Quotes are added only if necessary (i.e., if the string contains non-identifier characters or would be case-folded). Embedded quotes are properly doubled.', "quote_ident('Foo bar')", "'Foo bar'"),
                      ('quote_literal(string\xa0text)', 'text', 'Return the given string suitably quoted to be used as a string literal in an SQL statement string. Embedded single-quotes and backslashes are properly doubled. Note that quote_literal  returns null on null input; if the argument might be null, quote_nullable is often more suitable.', "quote_literal(E'O'Reilly')", "O''Reilly'"),
                      ('quote_literal(value\xa0anyelement)', 'text', 'Coerce the given value to text and then quote it as a literal. Embedded single-quotes and backslashes are properly doubled.', 'quote_literal(42.5)', "42.5'"),
                      ('quote_nullable(string\xa0text)', 'text', 'Return the given string suitably quoted to be used as a string literal in an SQL statement string; or, if the argument is null, return NULL. Embedded single-quotes and backslashes are properly doubled.', 'quote_nullable(NULL)', 'NULL'),
                      ('quote_nullable(value\xa0anyelement)', 'text', 'Coerce the given value to text and then quote it as a literal; or, if the argument is null, return NULL. Embedded single-quotes and backslashes are properly doubled.', 'quote_nullable(42.5)', "42.5'"),
                      ('regexp_matches(string\xa0text,\xa0pattern\xa0text\xa0[,\xa0flags\xa0text])', 'setof text[]', 'Return all captured substrings resulting from matching a POSIX regular expression against the string.', "regexp_matches('foobarbequebaz', '(bar)(beque)')", '{bar,beque}'),
                      ('regexp_replace(string\xa0text,\xa0pattern\xa0text,\xa0replacement\xa0text\xa0[,\xa0flags\xa0text])', 'text', 'Replace substring(s) matching a POSIX regular expression.', "regexp_replace('Thomas', '.[mN]a.', 'M')", 'ThM'),
                      ('regexp_split_to_array(string\xa0text,\xa0pattern\xa0text\xa0[,\xa0flags\xa0text\xa0])', 'text[]', 'Split string using a POSIX regular expression as the delimiter.', "regexp_split_to_array('hello world', E'\\s+')", '{hello,world}'),
                      ('regexp_split_to_table(string\xa0text,\xa0pattern\xa0text\xa0[,\xa0flags\xa0text])', 'setof text', 'Split string using a POSIX regular expression as the delimiter.', "regexp_split_to_table('hello world', E'\\s+')", 'helloworld(2 rows)'),
                      ('repeat(string\xa0text,\xa0number\xa0int)', 'text', 'Repeat string the specified number of times', "repeat('Pg', 4)", 'PgPgPgPg'),
                      ('replace(string\xa0text,\xa0from\xa0text,\xa0to\xa0text)', 'text', 'Replace all occurrences in string of substring from with substring to', "replace('abcdefabcdef', 'cd', 'XX')", 'abXXefabXXef'),
                      ('reverse(str)', 'text', 'Return reversed string.', "reverse('abcde')", 'edcba'), ('right(str\xa0text,\xa0n\xa0int)', 'text', 'Return last n characters in the string. When n is negative, return all but first |n| characters.', "right('abcde', 2)", 'de'),
                      ('rpad(string\xa0text,\xa0length\xa0int\xa0[,\xa0fill\xa0text])', 'text', 'Fill up the string to length length by appending the characters fill (a space by default). If the string is already longer than length then it is truncated.', "rpad('hi', 5, 'xy')", 'hixyx'),
                      ('rtrim(string\xa0text\xa0[,\xa0characters\xa0text])', 'text', 'Remove the longest string containing only characters from characters (a space by default) from the end of string', "rtrim('trimxxxx', 'x')", 'trim'),
                      ('split_part(string\xa0text,\xa0delimiter\xa0text,\xa0field\xa0int)', 'text', 'Split string on delimiter and return the given field (counting from one)', "split_part('abc~@~def~@~ghi', '~@~', 2)", 'def'),
                      ('strpos(string,\xa0substring)', 'int', 'Location of specified substring (same as position(substring in string), but note the reversed argument order)', "strpos('high', 'ig')", '2'),
                      ('substr(string,\xa0from\xa0[,\xa0count])', 'text', 'Extract substring (same as substring(string from from for count))', "substr('alphabet', 3, 2)", 'ph'),
                      ('to_ascii(string\xa0text\xa0[,\xa0encoding\xa0text])', 'text', 'Convert string to ASCII from another encoding (only supports conversion from LATIN1, LATIN2, LATIN9, and WIN1250 encodings)', "to_ascii('Karel')", 'Karel'),
                      ('to_hex(number\xa0int\xa0or\xa0bigint)', 'text', 'Convert number to its equivalent hexadecimal representation', 'to_hex(2147483647)', '7fffffff'),
                      ('translate(string\xa0text,\xa0from\xa0text,\xa0to\xa0text)', 'text', 'Any character in string that matches a character in the from set is replaced by the corresponding character in the to set. If from is longer than to, occurrences of the extra characters in from are removed.', "translate('12345', '143', 'ax')", 'a2x5')]

hitsListForTest = [
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903066',
        '_score': None,
        '_source': {
          'id': 903066,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:52:53 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-03 13:52:53',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:52:53',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903066
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903065',
        '_score': None,
        '_source': {
          'id': 903065,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:47:50 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-03 13:47:50',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:47:50',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903065
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903064',
        '_score': None,
        '_source': {
          'id': 903064,
          'logndx': 'ATIBA_VMWARE01_111',
          'socketaddress': '192.168.1.250:61778',
          'inetaddress': '192.168.1.250',
          'logdata': '<12>2021-02-03T10:55:50Z localhost.k3nc.com smartd: [warn] t10.ATA_____WDC_WD10EZRX2D00L4HB0_________________________WD2DWCC4J1054272: above TEMPERATURE threshold (116 > 0)',
          'port': '61778',
          'credate': '2021-02-03 13:45:58',
          'logrefval': '<12>',
          'logdate': '2021-02-03 10:55:50',
          'logservice': 'smartd',
          'logserviceno': 'warn',
          'severity': '4',
          'event': 't10.ATA_____WDC_WD10EZRX2D00L4HB0_________________________WD2DWCC4J1054272: above TEMPERATURE threshold (116 > 0)',
          'uniqueid': '448a5b2212c3',
          'outclass': 'Warning'
        },
        'sort': [
          903064
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903063',
        '_score': None,
        '_source': {
          'id': 903063,
          'logndx': 'ATIBA_VMWARE01_111',
          'socketaddress': '192.168.1.250:61778',
          'inetaddress': '192.168.1.250',
          'logdata': '<12>2021-02-03T10:55:50Z localhost.k3nc.com smartd: [warn] t10.ATA_____WDC_WD10EZRX2D00L4HB0_________________________WD2DWMC4J0200303: above TEMPERATURE threshold (116 > 0)',
          'port': '61778',
          'credate': '2021-02-03 13:45:58',
          'logrefval': '<12>',
          'logdate': '2021-02-03 10:55:50',
          'logservice': 'smartd',
          'logserviceno': 'warn',
          'severity': '4',
          'event': 't10.ATA_____WDC_WD10EZRX2D00L4HB0_________________________WD2DWMC4J0200303: above TEMPERATURE threshold (116 > 0)',
          'uniqueid': '448a5b2212c3',
          'outclass': 'Warning'
        },
        'sort': [
          903063
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903062',
        '_score': None,
        '_source': {
          'id': 903062,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:42:46 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-03 13:42:46',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:42:46',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903062
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903062',
        '_score': None,
        '_source': {
          'id': 903062,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:42:46 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-03 12:42:46',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:42:46',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903062
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903062',
        '_score': None,
        '_source': {
          'id': 903062,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:42:46 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-03 12:30:46',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:42:46',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903062
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903062',
        '_score': None,
        '_source': {
          'id': 903062,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:42:46 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-01 09:42:46',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:42:46',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903062
        ]
      },
      {
        '_index': 'atibalogs',
        '_type': '_doc',
        '_id': '903062',
        '_score': None,
        '_source': {
          'id': 903062,
          'logndx': '<341005>',
          'socketaddress': '192.168.1.50:514',
          'inetaddress': '192.168.1.50',
          'logdata': '<139>Feb  3 12:42:46 2021 192.168.1.50 cli[4163]: <341005> <ERRS> AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88>  Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'port': '514',
          'credate': '2021-02-02 11:12:46',
          'logrefval': '<139>',
          'logdate': '2021-02-03 12:42:46',
          'logservice': 'cli',
          'logserviceno': '4163',
          'severity': '3',
          'event': 'Failed to establish SSL connection with Activate:(10) ASN date error, current date after',
          'uniqueid': '186472c82788',
          'outclass': 'Error'
        },
        'sort': [
          903062
        ]
      }]

errorLogsHitsForTest = [
      {
        "_index" : "atibaloglar",
        "_type" : "_doc",
        "_id" : "747418",
        "_score" : "null",
        "_source" : {
          "severity" : "6",
          "classificationgroup" : "Info",
          "mappedlogsource" : "ap3",
          "socketaddress" : "192.168.1.50:514",
          "recstatus" : 2,
          "port" : "514",
          "olusturmatarih" : "2021-04-06 00:32:39.119",
          "tryjson" : 0,
          "logdate" : "2021-04-05 22:32:39",
          "recerror" : """MapperParsingException[failed to parse field [logdate] of type [date] in document with id '747418']; nested: IllegalArgumentException[Invalid format: "22:32:39" is malformed at ":32:39"];""",
          "inetaddress" : "192.168.1.50",
          "logdata" : "<142>Apr  5 23:32:39 2021 192.168.1.50 AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88> radiusd-term[26165]: Loaded virtual server <default>"
        },
        "sort" : [
          "747418"
        ]
      },
      {
        "_index" : "atibaloglar",
        "_type" : "_doc",
        "_id" : "747324",
        "_score" : "null",
        "_source" : {
          "severity" : "7",
          "classificationgroup" : "Debug",
          "mappedlogsource" : "ap3",
          "socketaddress" : "192.168.1.50:514",
          "recstatus" : 2,
          "port" : "514",
          "olusturmatarih" : "2021-04-06 00:32:36.734",
          "tryjson" : 0,
          "logdate" : "2021-04-05 22:32:34",
          "recerror" : """MapperParsingException[failed to parse field [logdate] of type [date] in document with id '747324']; nested: IllegalArgumentException[Invalid format: "22:32:34" is malformed at ":32:34"];""",
          "inetaddress" : "192.168.1.50",
          "logdata" : "<143>Apr  5 23:32:34 2021 192.168.1.50 AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88> sapd[4149]: S<< send_pwr_status_to_stm: pwr status aruba102 bssid = 18:64:72:02:78:82, actual_eirp=185, max_eirp=185"
        },
        "sort" : [
          "747324"
        ]
      },
      {
        "_index" : "atibaloglar",
        "_type" : "_doc",
        "_id" : "747322",
        "_score" : "null",
        "_source" : {
          "severity" : "7",
          "classificationgroup" : "Debug",
          "mappedlogsource" : "ap3",
          "socketaddress" : "192.168.1.50:514",
          "recstatus" : 2,
          "port" : "514",
          "olusturmatarih" : "2021-04-06 00:32:36.722",
          "tryjson" : 0,
          "logdate" : "2021-04-05 22:32:34",
          "recerror" : """MapperParsingException[failed to parse field [logdate] of type [date] in document with id '747322']; nested: IllegalArgumentException[Invalid format: "22:32:34" is malformed at ":32:34"];""",
          "inetaddress" : "192.168.1.50",
          "logdata" : "<143>Apr  5 23:32:34 2021 192.168.1.50 AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88> sapd[4149]: S<< send_pwr_status_to_stm: pwr status aruba002 bssid = 18:64:72:02:78:92, actual_eirp=270, max_eirp=285"
        },
        "sort" : [
          "747322"
        ]
      },
      {
        "_index" : "atibaloglar",
        "_type" : "_doc",
        "_id" : "747305",
        "_score" : "null",
        "_source" : {
          "severity" : "7",
          "classificationgroup" : "Debug",
          "mappedlogsource" : "ap3",
          "socketaddress" : "192.168.1.50:514",
          "recstatus" : 2,
          "port" : "514",
          "olusturmatarih" : "2021-04-06 00:32:36.489",
          "tryjson" : 0,
          "logdate" : "2021-04-05 22:32:34",
          "recerror" : """MapperParsingException[failed to parse field [logdate] of type [date] in document with id '747305']; nested: IllegalArgumentException[Invalid format: "22:32:34" is malformed at ":32:34"];""",
          "inetaddress" : "192.168.1.50",
          "logdata" : "<143>Apr  5 23:32:34 2021 192.168.1.50 AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88> sapd[4149]: S<< send_pwr_status_to_stm: pwr status aruba102 bssid = 18:64:72:02:78:82, actual_eirp=185, max_eirp=185"
        },
        "sort" : [
          "747305"
        ]
      },
      {
        "_index" : "atibaloglar",
        "_type" : "_doc",
        "_id" : "747303",
        "_score" : "null",
        "_source" : {
          "severity" : "7",
          "classificationgroup" : "Debug",
          "mappedlogsource" : "ap3",
          "socketaddress" : "192.168.1.50:514",
          "recstatus" : 2,
          "port" : "514",
          "olusturmatarih" : "2021-04-06 00:32:36.477",
          "tryjson" : 0,
          "logdate" : "2021-04-05 22:32:34",
          "recerror" : """MapperParsingException[failed to parse field [logdate] of type [date] in document with id '747303']; nested: IllegalArgumentException[Invalid format: "22:32:34" is malformed at ":32:34"];""",
          "inetaddress" : "192.168.1.50",
          "logdata" : "<143>Apr  5 23:32:34 2021 192.168.1.50 AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88> sapd[4149]: S<< send_pwr_status_to_stm: pwr status aruba002 bssid = 18:64:72:02:78:92, actual_eirp=270, max_eirp=285"
        },
        "sort" : [
          "747303"
        ]
      },
      {
        "_index" : "atibaloglar",
        "_type" : "_doc",
        "_id" : "747267",
        "_score" : "null",
        "_source" : {
          "severity" : "7",
          "classificationgroup" : "Debug",
          "mappedlogsource" : "ap3",
          "socketaddress" : "192.168.1.50:514",
          "recstatus" : 2,
          "port" : "514",
          "olusturmatarih" : "2021-04-06 00:32:35.892",
          "tryjson" : 0,
          "logdate" : "2021-04-05 22:32:34",
          "recerror" : """MapperParsingException[failed to parse field [logdate] of type [date] in document with id '747267']; nested: IllegalArgumentException[Invalid format: "22:32:34" is malformed at ":32:34"];""",
          "inetaddress" : "192.168.1.50",
          "logdata" : "<143>Apr  5 23:32:34 2021 192.168.1.50 AP:18:64:72:c8:27:88 <192.168.1.50 18:64:72:C8:27:88> sapd[4149]: S<< send_pwr_status_to_stm: pwr status aruba102 bssid = 18:64:72:02:78:82, actual_eirp=185, max_eirp=185"
        },
        "sort" : [
          "747267"
        ]
      }]


check_services_result_samples = {
    "head": {"active": 17, "inactive": 4},
    'active': [
        {'name': 'iamatiba-logger', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-elasticlogger', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-logarranger', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-parser', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-aianomaly', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-analyzer', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-causalgraphs', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-causality', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-djangoserver', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-httpmonitoring', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-icmpmonitoring', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-paramsmodelling', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-services', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-snmpcontroller', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-sqlmonitoring', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-timeseriescausality', 'code': 0, 'status': 'ok', 'is_running': True},
        {'name': 'iamatiba-uds', 'code': 0, 'status': 'ok', 'is_running': True}
    ],
    'inactive': [
        {'name': 'elasticsearch', 'code': 2, 'status': 'error info', 'is_running': False},
        {'name': 'iamatiba-anomaly', 'code': 768, 'status': 'error info', 'is_running': False},
        {'name': 'iamatiba-logseries', 'code': 768, 'status': 'error info', 'is_running': False},
        {'name': 'iamatiba-reporting', 'code': 768, 'status': 'error info', 'is_running': False}
    ]
}


def plotting_data(data_dictionary):
    pass

