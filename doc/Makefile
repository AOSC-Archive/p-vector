MD = $(shell ls *-*.md | sort)
MD2PDF = pandoc --pdf-engine xelatex --listings
MD2MAN = pandoc -s -t man
MD2CM = pandoc -t commonmark

all: p-vector.pdf p-vector.1.xz p-vector.commonmark

p-vector.pdf: $(MD)
	$(MD2PDF) -o $@ $(MD)

p-vector.1: $(MD)
	$(MD2MAN) -o $@ $(MD)

p-vector.1.xz: p-vector.1
	xz -z --keep $^

p-vector.commonmark: $(MD)
	$(MD2CM) -o $@ $(MD)
