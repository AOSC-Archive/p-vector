MD = $(shell ls *-*.md | sort)
MD2PDF = pandoc --pdf-engine xelatex --listings
MD2MAN = pandoc -s -t man

all: p-vector.pdf p-vector.1

p-vector.pdf: $(MD)
	$(MD2PDF) -o $@ $(MD)

p-vector.1: $(MD)
	$(MD2MAN) -o $@ $(MD)
