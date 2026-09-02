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
