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
