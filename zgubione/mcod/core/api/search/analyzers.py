from elasticsearch_dsl import analyzer, token_filter

from mcod import settings

__all__ = (
    "standard_analyzer",
    "polish_analyzer",
    "lang_synonyms_analyzers",
    "lang_exact_analyzers",
)

polish_hunspell = token_filter("pl", type="hunspell", locale="pl_PL", dedup=True)

polish_stopwords = token_filter("polish_stopwords", type="stop", ignore_case=True, stopwords_path="stopwords.txt")

en_synonym_filter = token_filter("english_synonym_filter", **settings.ES_EN_SYN_FILTER_KWARGS)
pl_synonym_filter = token_filter("polish_synonym_filter", **settings.ES_PL_SYN_FILTER_KWARGS)


standard_analyzer = analyzer(
    "standard_analyzer",
    tokenizer="standard",
    filter=["standard", polish_stopwords, "lowercase"],
    char_filter=["html_strip"],
)

standard_asciied = analyzer(
    "standard_analyzer",
    tokenizer="standard",
    filter=["lowercase", "asciifolding", "trim"],
    char_filter=["html_strip"],
)

polish_analyzer = analyzer(
    "polish_analyzer",
    tokenizer="standard",
    filter=["standard", polish_stopwords, "lowercase", polish_hunspell],
    char_filter=["html_strip"],
)

polish_synonym = analyzer(
    "polish_synonym_analyzer",
    tokenizer="standard",
    filter=[
        "standard",
        polish_stopwords,
        "lowercase",
        pl_synonym_filter,
        polish_hunspell,
    ],
    char_filter=["html_strip"],
)

polish_exact = analyzer(
    "polish_exact_analyzer",
    type="custom",
    tokenizer="whitespace",
    filter=[
        "stop",
    ],
    char_filter=["html_strip"],
)

pl_ascii_folding = token_filter("pl_ascii_folding", type="asciifolding", preserve_original=True)

polish_asciied = analyzer(
    "polish_asciied",
    type="custom",
    tokenizer="standard",
    filter=["lowercase", pl_ascii_folding, "trim"],
    char_filter=["html_strip"],
)

english_synonym = analyzer(
    "english_synonym_analyzer",
    tokenizer="standard",
    filter=["standard", "lowercase", en_synonym_filter],
    char_filter=["html_strip"],
)

english_exact = analyzer(
    "english_exact_analyzer",
    type="custom",
    tokenizer="whitespace",
    filter=[
        "stop",
    ],
    char_filter=["html_strip"],
)

autocomplete_filter = token_filter("autocomplete_filter", type="edge_ngram", min_gram=3, max_gram=15)

autocomplete_analyzer = analyzer(
    "autocomplete_analyzer",
    type="custom",
    tokenizer="standard",
    filter=["lowercase", autocomplete_filter],
)

lang_synonyms_analyzers = {"pl": polish_synonym, "en": english_synonym}
lang_exact_analyzers = {"pl": polish_exact, "en": english_exact}
autocomplete_analyzers = {"pl": autocomplete_analyzer, "en": autocomplete_analyzer}
