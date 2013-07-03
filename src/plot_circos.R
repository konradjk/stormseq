#!/usr/bin/env Rscript

library(argparse)
library(ggbio)
library(biovizBase)

parser <- ArgumentParser()
parser$add_argument("-s", "--sample")
args <- parser$parse_args()
s = args$sample

chr.sub <- c(paste("chr", c(1:22), sep = ""), 'chrX', 'chrY')

full_ideo = getIdeogram('hg19')
raw_ideo = getIdeogram('hg19', cytoband=FALSE)

snpden = read.table(paste('/mydata/', s, '.vcf.snpden', sep=''), header=T)
data = with(snpden, GRanges(CHROM, IRanges(BIN_START, width = 1000000)))
values(data) = data.frame(density=snpden$SNPS.KB)
data = keepSeqlevels(data, chr.sub)
chr.sub = levels(data@seqnames)
data = keepSeqlevels(data, chr.sub)

ideo = keepSeqlevels(raw_ideo, chr.sub)
centromeres = full_ideo[full_ideo@elementMetadata$gieStain == 'acen',]
centromeres = keepSeqlevels(centromeres, chr.sub)
seqlengths(centromeres) = seqlengths(ideo)
centromeres = union(centromeres, centromeres)
seqlengths(data) = seqlengths(ideo)

p = ggplot() + layout_circle(ideo, geom = "ideo", fill = "gray70", radius = 30, trackWidth = 2)
p = p + layout_circle(centromeres, geom = "rect", color = "red", radius = 30, trackWidth = 2)
p = p + layout_circle(ideo, geom = "text", aes(label = seqnames), vjust = 0, radius = 32, trackWidth = 2, cex=3.5)
p = p + layout_circle(data, geom = 'line', aes(y = density), color = "red", radius = 15, trackWidth = 12, cex = 0.2)
pdf(paste('/mydata/', s, '_circos.pdf', sep=''), height=16, width=16)
print(p)
dev.off()
png(paste('/mydata/', s, '_circos.png', sep=''), width=800, height=800)
print(p)
dev.off()
