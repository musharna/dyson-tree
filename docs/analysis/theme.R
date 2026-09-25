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
shapes_mark <- c(`measured later root (not the edge)` = 124, `prereg expected: the edge` = 1,
                 `prereg expected: a later root` = 5)
scale_shape_mark <- function(...) scale_shape_manual(values = shapes_mark, ...)
# A prereg expected mark is drawn this far (in rows) below its measured mark, so a value that
# coincides with the measurement to 1e-5 AU is still a visible, separate mark (data unchanged).
expected_nudge <- -0.3
# Registered band: one fill, scoped to the registered row only.
band_fill <- "grey40"
band_alpha <- 0.12
# Measured-to-expected connector: thin dotted grey, never confusable with a "|" point glyph.
connector_colour <- "grey60"
connector_linetype <- "dotted"
connector_width <- 0.45
# Value labels on points: >= 12 px at 150 dpi.
value_label_size <- 3.6
