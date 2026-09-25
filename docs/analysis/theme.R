# House ggplot2 theme for dyson-tree. EVERY plot script sources this file.
# Restyle here, never inline in a plot script.
suppressPackageStartupMessages(library(ggplot2))

palette_dyson <- c(vascular = "#2E7D32", algal = "#1565C0")

theme_dyson <- function(base_size = 12) {
  theme_minimal(base_size = base_size) +
    theme(
      panel.grid.minor = element_blank(),
      plot.title.position = "plot",
      legend.position = "bottom",
      strip.text = element_text(face = "bold")
    )
}

scale_colour_dyson <- function(...) scale_colour_manual(values = palette_dyson, ...)
scale_fill_dyson <- function(...) scale_fill_manual(values = palette_dyson, ...)

# Vessel failure classes (Q4): one palette, used identically by every figure.
palette_failure <- c(HELD = "#6A9F3A", FREEZE = "#5DA5DA", STARVE = "#B07AA1", OPAQUE = "#4D4D4D")
scale_colour_failure <- function(...) scale_colour_manual(values = palette_failure, ...)
scale_fill_failure <- function(...) scale_fill_manual(values = palette_failure, ...)
# Tolerance verdict on a compared row: neither colour is a failure-class colour.
palette_tolerance <- c(within = "#000000", outside = "#D81B60")
scale_colour_tolerance <- function(...) scale_colour_manual(values = palette_tolerance, ...)
# Stress sigma (MPa) is encoded by shape, never colour.
shapes_sigma <- c(`0.7` = 16, `1.5` = 17, `3.1` = 15)
scale_shape_sigma <- function(...) scale_shape_manual(values = shapes_sigma, ...)
# Mark vocabulary for measured-vs-prereg figures: one mark per meaning.
shapes_mark <- c(`measured later root (not the edge)` = 4, `prereg expected: the edge` = 1,
                 `prereg expected: a later root` = 5)
scale_shape_mark <- function(...) scale_shape_manual(values = shapes_mark, ...)
# A prereg expected mark is drawn this far (in rows) below its measured mark, so a value that
# coincides with the measurement to 1e-5 AU is still a visible, separate mark (data unchanged).
expected_nudge <- -0.42
# Registered band: one fill, scoped to the registered row only.
band_fill <- "grey40"
band_alpha <- 0.12
# Measured-to-expected connector: thin dotted grey, never confusable with a "|" point glyph.
connector_colour <- "grey10"
connector_linetype <- "22"  # short dashes: a dotted line this short reads as specks
connector_width <- 0.8
# Value labels on points: >= 12 px at 150 dpi.
value_label_size <- 3.6
# Measured later root ("x" glyph): readable, and unlike a link or a diamond.
later_root_size <- 3.2
# A link stops this far (rows) short of each mark's centre: about one marker radius, so it never enters it.
link_gap <- 0.1
# Later roots sit this far (rows) above the row line, so a root next to the edge never covers its dot.
root_lift <- 0.14
# A later root's prereg expected sits here (rows, above its own row line): < 0.5, so it reads as its row's.
root_expected_dy <- 0.44
# P2 edge expecteds: below their dot by this much (rows); well under half a row.
edge_expected_dy_p2 <- -0.3
