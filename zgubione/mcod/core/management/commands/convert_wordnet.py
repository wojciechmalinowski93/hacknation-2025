from django_tqdm import BaseCommand
from lxml import etree


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("inputfile", type=str)
        parser.add_argument("outputfile", type=str)

    @staticmethod
    def convert_wordnet_to_solr(input_path, output_path):
        outfile = open(output_path, "w")

        for event, element in etree.iterparse(input_path, tag="SYNSET"):
            if element.find("POS").text == "n":
                literals = [literal.text for literal in element.find("SYNONYM").findall("LITERAL")]
                if len(literals) > 1:
                    outfile.write(",".join(literals) + "\n")
            element.clear()

    def handle(self, *args, **options):
        self.convert_wordnet_to_solr(options["inputfile"], options["outputfile"])
