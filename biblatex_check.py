#!/usr/bin/env python

"""
BibLaTeX check on missing fields and consistent name conventions,
especially developed for requirements in Computer Science.
"""

__author__ = "Pez Cuckow"
__version__ = "1.0.0"
__credits__ = ["Pez Cuckow", "BibTex Check 0.2.0 by Fabian Beck"]
__license__ = "MIT"
__email__ = "email<at>pezcuckow.com"

####################################################################
# Properties (please change according to your needs)
####################################################################

# links
citeulikeUsername = ""  # if no username is provided, no CiteULike links appear
citeulikeHref = "http://www.citeulike.org/user/" + citeulikeUsername + "/article/"

libraries = [
    ("Scholar", "http://scholar.google.de/scholar?hl=en&q="),
    ("Google", "https://www.google.com/search?q="),
    ("DBLP", "http://dblp.org/search/index.php#query="),
    ("IEEE", "http://ieeexplore.ieee.org/search/searchresult.jsp?queryText="),
    ("ACM", "http://dl.acm.org/results.cfm?query="),
]

# fields that are required for a specific type of entry
requiredEntryFields = {
    "article": ["author", "title", "journal", "year"],
    "book": ["author", "title", "year"],
    "mvbook": "book",
    "inbook": ["author", "title", "booktitle", "year"],
    "bookinbook": "inbook",
    "suppbook": "inbook",
    "booklet": ["author", "title", "year"],
    "collection": ["editor", "title", "year"],
    "mvcollection": "collection",
    "incollection": ["author", "title", "booktitle", "year"],
    "suppcollection": "incollection",
    "manual": ["author", "title", "year"],
    "misc": ["author", "title", "year"],
    "online": ["author", "title", "year", "url"],
    "patent": ["author", "title", "number", "year"],
    "periodical": ["editor", "title", "year"],
    "suppperiodical": "article",
    "proceedings": ["title", "year"],
    "mvproceedings": "proceedings",
    "inproceedings": ["author", "title", "booktitle", "year"],
    "reference": "collection",
    "mvreference": "collection",
    "inreference": "incollection",
    "report": ["author", "title", "type", "institution", "year"],
    "thesis": ["author", "title", "type", "institution", "year"],
    "unpublished": ["author", "title", "year"],
    # semi aliases (differing fields)
    "mastersthesis": ["author", "title", "institution", "year"],
    "techreport": ["author", "title", "institution", "year"],
    # other aliases
    "conference": "inproceedings",
    "electronic": "online",
    "phdthesis": "mastersthesis",
    "www": "online",
    "school": "mastersthesis",
}

# BibLaTeX has backwards compatibility with BibTeX for these fiends
fieldAliases = {"school": "institution", "address": "location"}

####################################################################

import string
import re
import sys
from optparse import OptionParser

### Parse Args ###

usage = (
        sys.argv[0]
        + " [-b|--bib=<input.bib>] [-a|--aux=<input.aux>] [-o|--output=<output.html>] [-v|--view] [-h|--help]"
)

parser = OptionParser(usage)

parser.add_option(
    "-b",
    "--bib",
    dest="bibFile",
    help="Bib File",
    metavar="input.bib",
    default="input.bib",
)

parser.add_option(
    "-a",
    "--aux",
    dest="auxFile",
    help="Aux File",
    metavar="input.aux",
    default="references.aux",
)

parser.add_option(
    "-o", "--output", dest="htmlOutput", help="HTML Output File", metavar="output.html"
)

parser.add_option(
    "-v", "--view", dest="view", action="store_true", help="Open in Browser"
)

parser.add_option(
    "-N",
    "--no-console",
    dest="no_console",
    action="store_true",
    help="Do not print problems to console",
)

(options, args) = parser.parse_args()

### Backport Python 3 open(encoding="utf-8") to Python 2 ###
# based on http://stackoverflow.com/questions/10971033/backporting-python-3-openencoding-utf-8-to-python-2

if sys.version_info[0] > 2:
    # py3k
    pass
else:
    # py2
    import codecs
    import warnings

    reload(sys)
    sys.setdefaultencoding("utf8")


    def open(
            file,
            mode="r",
            buffering=-1,
            encoding=None,
            errors=None,
            newline=None,
            closefd=True,
            opener=None,
    ):
        if newline is not None:
            warnings.warn("newline is not supported in py2")
        if not closefd:
            warnings.warn("closefd is not supported in py2")
        if opener is not None:
            warnings.warn("opener is not supported in py2")
        return codecs.open(
            filename=file,
            mode=mode,
            encoding=encoding,
            errors=errors,
            buffering=buffering,
        )

### Handle Args ###

print("INFO: Reading references from '" + options.bibFile + "'")
try:
    fIn = open(options.bibFile, "r", encoding="utf8")
except IOError as e:
    print(
        "ERROR: Input bib file '"
        + options.bibFile
        + "' doesn't exist or is not readable"
    )
    sys.exit(-1)

if options.no_console:
    print("INFO: Will suppress problems on console")

if options.htmlOutput:
    print(
        "INFO: Will output HTML to '"
        + options.htmlOutput
        + "'"
        + (" and auto open in the default web browser" if options.view else "")
    )

# Filter by reference ID's that are used
usedIds = set()
if options.auxFile:
    print("INFO: Filtering by references found in '" + options.auxFile + "'")
    try:
        fInAux = open(options.auxFile, "r", encoding="utf8")
        for auxLine in fInAux:
            if auxLine.startswith("\\citation"):
                entryIds = auxLine.split("{")[1].rstrip("} \n").split(", ")
                for entryId in entryIds:
                    if entryId != "":
                        usedIds.add(entryId)
        fInAux.close()
    except IOError as e:
        print(
            "WARNING: Aux file '"
            + options.auxFile
            + "' doesn't exist -> not restricting entries"
        )

### Methods ###

removePunctuationMap = dict((ord(char), None) for char in string.punctuation)


def resolveAliasedRequiredFields(entryRequiredFields, requiredFieldsDict):
    # Aliases use a string to point at another set of fields
    while isinstance(entryRequiredFields, str):
        entryRequiredFields = requiredFieldsDict.get(entryRequiredFields)

    return entryRequiredFields


def generateEntryProblemsHTML(
        itemHTML, itemId, type, articleId, title, problems, author, lineNumber
):
    cleanedTitle = title.translate(removePunctuationMap)
    html = "<div id='" + itemId + "' class='problem severe" + str(len(problems)) + "'>"
    html += "<h2>" + itemId + " (" + type + ")</h2> "
    html += "<div class='links'>"
    if citeulikeUsername:
        html += (
                "<a href='"
                + citeulikeHref
                + articleId
                + "' target='_blank'>CiteULike</a> |"
        )

    librariesList = []
    for name, site in libraries:
        librariesList.append(
            " <a href='" + site + cleanedTitle + "' target='_blank'>" + name + "</a>"
        )
    html += " | ".join(librariesList)

    html += "</div>"
    html += "<div class='reference'>" + title + " (" + author + ")"
    html += "</div>"
    html += "<ul>"

    for subproblem in problems:
        html += "<li>" + subproblem + "</li>"
        if not options.no_console:
            errorMessage = "PROBLEM: {}:{} - {} - {}\n".format(
                options.bibFile, lineNumber, itemId, subproblem
            )
            sys.stderr.write(errorMessage)

    html += "</ul>"
    html += "<form class='problem_control'><label>checked</label><input type='checkbox' class='checked'/></form>"
    html += "<div class='bibtex_toggle'>Current BibLaTex Entry</div>"
    html += "<div class='bibtex'>" + itemHTML + "</div>"
    html += "</div>"

    return html


### Globals ###

entriesIds = []
entriesProblemsHTML = []

entryArticleId = ""
entryAuthor = ""
entryFields = []
entryHTML = ""
entryId = ""
entryProblems = []
entryTitle = ""
entryType = ""

counterFlawedNames = 0
counterMissingCommas = 0
counterMissingFields = 0
counterNonUniqueId = 0
counterWrongFieldNames = 0
counterWrongTypes = 0
counterExtraFields = 0  # счетчик лишних полей#

lastLine = 0

foreign_language_count = 0
articles_after_2010_count = 0
literature_21_century_count = 0
total_count = 0


### Global Abusing Handlers ###


def handleNewEntryStarting(line):
    global entryArticleId, entryAuthor, entryFields, entryHTML, entryId, entryProblems, entryTitle, entryType
    global counterMissingCommas, counterNonUniqueId

    entryFields = []
    entryProblems = []

    entryId = line.split("{")[1].rstrip(",\n")

    if line[-1] != ",":
        entryProblems.append("missing comma at '@" + entryId + "' definition")
        counterMissingCommas += 1

    if entryId in entriesIds:
        entryProblems.append("non-unique id: '" + entryId + "'")
        counterNonUniqueId += 1
    else:
        entriesIds.append(entryId)

    entryType = line.split("{")[0].strip("@ ")
    entryHTML = line + "<br />"


def handleEntryEnding(lineNumber, line):
    global entryArticleId, entryAuthor, entryFields, entryHTML, entryId, entryProblems, entryTitle, entryType
    global counterMissingFields, counterMissingCommas, removePunctuationMap
    global entriesProblemsHTML
    global lastLine

    # Last line of entry is allowed to have missing comma
    if lastLine == lineNumber - 1:
        entryProblems = entryProblems[:-1]
        counterMissingCommas -= 1

    # Support for type aliases
    entryFields = list(map(
        lambda typeName: fieldAliases.get(typeName)
        if typeName in fieldAliases
        else typeName,
        entryFields,
    ))

    entryHTML += line + "<br />"

    if entryId in usedIds or not usedIds:
        entryRequiredFields = requiredEntryFields.get(entryType.lower())
        entryRequiredFields = resolveAliasedRequiredFields(
            entryRequiredFields, requiredEntryFields
        )

        for requiredEntryField in entryRequiredFields:
            # support for author/editor syntax
            requiredEntryField = requiredEntryField.split("/")

            # at least one the required fields is not found
            if set(requiredEntryField).isdisjoint(entryFields):
                entryProblems.append(
                    "missing field '" + "/".join(requiredEntryField) + "'"
                )
                counterMissingFields += 1

    else:
        entryProblems = []

    if entryId in usedIds or (entryId and not usedIds):
        entryProblemsHTML = generateEntryProblemsHTML(
            entryHTML,
            entryId,
            entryType,
            entryArticleId,
            entryTitle,
            entryProblems,
            entryAuthor,
            lineNumber,
        )
        entriesProblemsHTML.append(entryProblemsHTML)


def handleEntryLine(lineNumber, line):
    global entryHTML, entryId
    global usedIds

    if line != "":
        entryHTML += line + "<br />"

    if entryId in usedIds or not usedIds:
        if "=" in line:
            handleEntryField(lineNumber, line)


def detect_language(text):
    # Проверка наличия русских символов в тексте
    for char in text:
        if 'а' <= char <= 'я' or 'А' <= char <= 'Я':
            return 'russian'
    return 'english'


def handleEntryField(lineNumber, line):
    global entryArticleId, entryAuthor, entryFields, entryHTML, entryId, entryProblems, entryTitle, entryType
    global counterFlawedNames, counterWrongTypes, counterWrongFieldNames, counterMissingCommas, counterExtraFields
    global lastLine, foreign_language_count, articles_after_2010_count, literature_21_century_count, total_count


    if line.strip().startswith("%"):
        # Игнорируем строки, начинающиеся с символа '%'
        return

    fieldName = line.split("=")[0].strip().lower()  # biblatex is not case sensitive
    fieldValue = line.split("=")[1].strip(", \n").strip("{} \n")

    entryFields.append(fieldName)

    if fieldName == "title":
        total_count += 1
        entryTitle = re.sub(r"\}|\{", r"", fieldValue)
        # Проверка языка заголовка
        language = detect_language(entryTitle)
        if language == 'english':
            # Прибавляю к англоязычным статьям
            foreign_language_count +=1
            # Если статья англоязычная, проверяем наличие тома и страниц
            if "article" in entryType.lower():
                if "volume" not in entryFields:
                    entryProblems.append("отсутствует поле 'volume' в английской статье")
                if "pages" not in entryFields:
                    entryProblems.append("отсутствует поле 'pages' в английской статье")

    # Checks per field type
    if fieldName == "author":
        entryAuthor = "".join(filter(lambda x: not (x in '\\"{}'), fieldValue.split(" and ")[0]))
        for author in fieldValue.split(" and "):
            comp = author.split(",")
            if len(comp) == 0:
                entryProblems.append(
                    "too little name components for an author in field 'author'"
                )
            elif len(comp) > 2:
                entryProblems.append(
                    "too many name components for an author in field 'author'"
                )
            elif len(comp) == 2:
                if comp[0].strip() == "":
                    entryProblems.append(
                        "last name of an author in field 'author' empty"
                    )
                if comp[1].strip() == "":
                    entryProblems.append(
                        "first name of an author in field 'author' empty"
                    )

    if fieldName == "year":
        year_value = int(fieldValue)
        if year_value > 2010:
            articles_after_2010_count += 1
        if year_value >= 2001:
            literature_21_century_count  += 1

    elif fieldName == "citeulike-article-id":
        entryArticleId = fieldValue

    elif fieldName == "title":
        entryTitle = re.sub(r"\}|\{", r"", fieldValue)

    ###############################################################
    # Checks (please (de)activate/extend to your needs)
    ###############################################################

    # check if type 'proceedings' might be 'inproceedings'
    elif entryType == "proceedings" and fieldName == "pages":
        entryProblems.append(
            "wrong type: maybe should be 'inproceedings' because entry has page numbers"
        )
        counterWrongTypes += 1

    # check if abbreviations are used in journal titles
    elif entryType == "article" and fieldName in ("journal", "journaltitle"):
        if "." in line:
            entryProblems.append(
                "flawed name: abbreviated journal title '" + fieldValue + "'"
            )
            counterFlawedNames += 1

    # check booktitle format; expected format "ICBAB '13: Proceeding of the 13th International Conference on Bla and Blubb"
    # if entryType == "inproceedings" and fieldName == "booktitle":
    # if ":" not in line or ("Proceedings" not in line and "Companion" not in line) or "." in line or " '" not in line or "workshop" in line or "conference" in line or "symposium" in line:
    # entryProblems.append("flawed name: inconsistent formatting of booktitle '"+fieldValue+"'")
    # counterFlawedNames += 1

    # check if title is capitalized (heuristic)
    # if fieldName == "title":
    # for word in entryTitle.split(" "):
    # word = word.strip(":")
    # if len(word) > 7 and word[0].islower() and not  "-" in word and not "_"  in word and not "[" in word:
    # entryProblems.append("flawed name: non-capitalized title '"+entryTitle+"'")
    # counterFlawedNames += 1
    # break

    # check for commas at end of line
    if line[-1] != ",":
        counterMissingCommas += 1
        entryProblems.append(
            "missing comma at end of line, at '" + fieldName + "' field definition."
        )
        lastLine = lineNumber

    # Проверяем наличие лишних полей
    if fieldName not in requiredEntryFields.get(entryType.lower(), []):
        entryProblems.append("лишнее поле '" + fieldName + "'")
        counterExtraFields += 1

### Parse input file ###

for (bibLineNumber, bibLine) in enumerate(fIn):
    bibLine = bibLine.strip("\n")

    # Starting a new entry
    if bibLine.startswith("@"):
        handleNewEntryStarting(bibLine)

    # Closing out the current entry
    elif bibLine.startswith("}"):
        handleEntryEnding(bibLineNumber, bibLine)

    else:
        handleEntryLine(bibLineNumber, bibLine)

fIn.close()

problemCount = (
        counterMissingFields
        + counterFlawedNames
        + counterWrongFieldNames
        + counterWrongTypes
        + counterNonUniqueId
        + counterMissingCommas
        + counterExtraFields
)

# Write out our HTML file
if options.htmlOutput:
    html = open(options.htmlOutput, "w", encoding="utf8")
    html.write(
        """<!doctype html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>BibLatex Check</title>
<style>
body {
    font-family: Calibri, Arial, Sans;
    padding: 10px;
    width: 1030px;
    margin: 10px auto;
    border-top: 1px solid black;
}

#title {
    width: 720px;
    border-bottom: 1px solid black;
}

#title h1 {
    margin: 10px 0px;
}

#title h1 a {
    color: black;
    text-decoration: none;
}

#control {
    clear: both;
}

#search {
    float: left;
}

#search input {
    width: 300px;
    font-size: 14pt;
}

#mode {
    text-align: right;
}

#mode label:first-child {
    font-weight: bold;
}

#mode input {
    margin-left: 20px;
}

.info {
    margin-top: 10px;
    padding: 10px;
    background: #FAFADD;
    width: 250px;
    float: right;
    box-shadow: 1px 1px 1px 1px #ccc;
    clear: both;
}

.info h2 {
    font-size: 12pt;
    padding: 0px;
    margin: 0px;
}

.correspondence {

}

.square {
    width: 50px;
    height: 50px;
    margin-right: 10px;
    margin-bottom: 10px;
    font-size: 20px;
    font-weight: bold;
    display: inline-block;
    text-align: center; /* Add this property to center the text */
    line-height: 50px; /* Add this property to vertically center the text */
}

.problem {
    margin-top: 10px;
    margin-bottom: 10px;
    padding: 10px;
    background: #FFBBAA;
    counter-increment: problem;
    width: 700px;
    border: 1px solid #993333;
    border-left: 5px solid #993333;
    box-shadow: 1px 1px 1px 1px #ccc;
    float: left;
}

.active {
    box-shadow: 5px 5px 3px 3px #ccc;
    position: relative;
    top: -2px;
}

.severe0 {
    background: #FAFAFA;
    border: 1px solid black;
    border-left: 5px solid black;
}

.severe1 {
    background: #FFEEDD;
}

.severe2 {
    background: #FFDDCC;
}

.severe3 {
    background: #FFCCBB;
}

.problem_checked {
    border: 1px solid #339933;
    border-left: 5px solid #339933;
}

.problem h2:before {
    content: counter(problem) ". "; color: gray;
}

.problem h2 {
    font-size: 12pt;
    padding: 0px;
    margin: 0px;
}

.problem .links {
    float: right;
    position:relative;
    top: -22px;
}

.problem .links a {
    color: #3333CC;
}

.problem .links a:visited {
    color: #666666;
}

.problem .reference {
    clear: both;
    font-size: 9pt;
    margin-left: 20px;
    font-style:italic;
    font-weight:bold;
}

.problem ul {
    clear: both;
}

.problem .problem_control {
    float: right;
    margin: 0px;
    padding: 0px;
}

.problem .bibtex_toggle{
    text-decoration: underline;
    font-size: 9pt;
    cursor: pointer;
    padding-top: 5px;
}

.problem .bibtex {
    margin-top: 5px;
    font-family: Monospace;
    font-size: 8pt;
    display: none;
    border: 1px solid black;
    background-color: #FFFFFF;
    padding: 5px;
}
</style>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.5/jquery.min.js"></script>
<script>

function isInProblemMode() {
    return $('#mode_problems:checked').val() == 'problems'
}

function update() {
    if ($('#search input').val() !== "") {
        $('.problem').hide();
        $('.problem[id*='+$('#search input').val()+' i]').show();
    } else {
        $('.problem').show();
    }
    $('.problem .checked').each(function () {
        if ($(this).attr('checked')) {
            $(this).parents('.problem').addClass('problem_checked');
        } else {
            $(this).parents('.problem').removeClass('problem_checked');
        }
    });
    if (isInProblemMode()) {
        $('.severe0').hide();
        $('.problem_checked').hide();
    }
}

$(document).ready(function(){

    $(".bibtex_toggle").click(function(event){
        event.preventDefault();
        $(this).next().slideToggle();
    });

    $('#search input').live('input', function() {
        update();
    });

    $('#mode input').change(function() {
        update();
    });

    $("#uncheck_button").click(function(){
        $('.problem .checked').attr('checked',false);
        localStorage.clear();
        update();
    });

    $('.problem a').mousedown(function(event) {
        $('.problem').removeClass('active');
        $(this).parents('.problem').addClass('active');
    });

    $('.problem .checked').change(function(event) {
        var problem = $(this).parents('.problem');
        problem.toggleClass('problem_checked');
        var checked = problem.hasClass('problem_checked');
        localStorage.setItem(problem.attr('id'),checked);
        if (checked && isInProblemMode()) {
            problem.slideUp();
        }
    });

    $('.problem .checked').each(function () {
        $(this).attr('checked',localStorage.getItem($(this).parents('.problem').attr('id'))=='true');
    });
    update();
});

</script>
</head>
<body>
<div id="title">
<h1><a href='http://github.com/pezmc/BibLatex-Check'>BibLaTeX Check</a></h1>
<div id="control">
<form id="search"><input placeholder="search entry ID ..."/></form>
<form id="mode">
<label>show entries:</label>
<input type = "radio"
                 name = "mode"
                 id = "mode_problems"
                 value = "problems"
                 checked = "checked" />
          <label for = "mode_problems">problems</label>
          <input type = "radio"
                 name = "mode"
                 id = "mode_all"
                 value = "all" />
          <label for = "mode_all">all</label>
<input type="button" value="uncheck all" id="uncheck_button"></button>
</form>
<br style="clear: both; " />
</div>
</div>
"""
    )

    # Функция для определения цвета квадратика в зависимости от условий
    def get_square_color(gg, total_count, foreign_language_count, articles_after_2010_count, literature_21_century_count):
        if (
                (gg == 5 or gg == 6) and total_count > 30 and foreign_language_count > 6 and articles_after_2010_count > 6 and literature_21_century_count > 20):
            return 'red'
        if (
                gg == 4 and total_count > 25 and foreign_language_count > 5 and articles_after_2010_count > 6 and literature_21_century_count > 20):
            return 'orange'
        if (
                gg == 3 and total_count > 20 and foreign_language_count > 4 and articles_after_2010_count > 4 and literature_21_century_count > 14):
            return 'yellow'
        if (
                gg == 2 and total_count > 15 and foreign_language_count > 3 and articles_after_2010_count > 2 and literature_21_century_count > 9):
            return 'green'
        else:
            return 'gray'


    # HTML для блока "СООТВЕТСТВИЕ"
    square_colors = {
        '2': get_square_color( 2, total_count, foreign_language_count, articles_after_2010_count, literature_21_century_count),
        '3': get_square_color( 3, total_count, foreign_language_count, articles_after_2010_count,
                              literature_21_century_count),
        '4': get_square_color( 4, total_count, foreign_language_count, articles_after_2010_count,
                              literature_21_century_count),
        '5': get_square_color( 5, total_count, foreign_language_count, articles_after_2010_count,
                              literature_21_century_count),
        '6': get_square_color( 6, total_count, foreign_language_count, articles_after_2010_count,
                              literature_21_century_count),
    }


    html.write("<div class='info'><h2>Info</h2><ul>")
    html.write("<li>bib file: " + options.bibFile + "</li>")
    html.write("<li>aux file: " + options.auxFile + "</li>")
    html.write("<li># записей с ошибками: " + str(len(entriesProblemsHTML)) + "</li>")
    html.write("<li># проблем: " + str(problemCount) + "</li><ul>")
    html.write("<li># отстутвующие поля: " + str(counterMissingFields) + "</li>")
    html.write("<li># ошибочные имиена: " + str(counterFlawedNames) + "</li>")
    html.write("<li># неправильные типы: " + str(counterWrongTypes) + "</li>")
    html.write("<li># неуникальный идентитификатор: " + str(counterNonUniqueId) + "</li>")
    html.write("<li># неправильное поле: " + str(counterWrongFieldNames) + "</li>")
    html.write("<li># отсутствует запятая: " + str(counterMissingCommas) + "</li>")
    html.write("<li># лишнее поле: " + str(counterExtraFields) + "</li>")
    html.write("</ul></ul>")
    html.write("<div id='correspondence' class='correspondence'>")
    html.write("<h2>СООТВЕТСТВИЕ</h2>")
    html.write("<div class='square' style='background-color:" + square_colors['2'] + ";'>2</div>")
    html.write("<div class='square' style='background-color:" + square_colors['3'] + ";'>3</div>")
    html.write("<div class='square' style='background-color:" + square_colors['4'] + ";'>4</div>")
    html.write("<div class='square' style='background-color:" + square_colors['5'] + ";'>5</div>")
    html.write("<div class='square' style='background-color:" + square_colors['6'] + ";'>6</div>")
    html.write("</div>")
    html.write("</div>")



    entriesProblemsHTML.sort()
    for problem in entriesProblemsHTML:
        html.write(problem)
    html.write("</body></html>")
    html.close()

    if options.view:
        import os
        import pathlib
        import webbrowser

        webbrowser.open(pathlib.Path(os.path.abspath(html.name)).as_uri())

    print("SUCCESS: Report {} has been generated".format(options.htmlOutput))

if problemCount > 0:
    print("WARNING: Found {} problems.".format(problemCount))
    sys.exit(-1)