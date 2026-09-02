#!/usr/bin/env Rscript
# Two figures from the Q1 CSVs. One graph per figure. Reads CSVs only.
args <- commandArgs(trailingOnly = TRUE)
here <- normalizePath(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE))))
in_dir <- if (length(args) >= 1) args[1] else here
repo <- normalizePath(file.path(here, "..", ".."))
source(file.path(repo, "docs", "analysis", "theme.R"))

sweep <- read.csv(file.path(in_dir, "sweep.csv"), comment.char = "#")
cross <- read.csv(file.path(in_dir, "crossover.csv"), comment.char = "#")
stopifnot(nrow(sweep) > 0, nrow(cross) > 0)
sweep$k <- factor(sweep$k)
cross$k <- as.numeric(cross$k)
fig_dir <- file.path(in_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE)

# Figure 1: net carbon vs distance, per class, k as linetype
p1 <- ggplot(sweep, aes(r_au, net_carbon, colour = class, linetype = k)) +
  geom_hline(yintercept = 0, colour = "grey40") +
  geom_line() +
  scale_x_log10() +
  coord_cartesian(ylim = c(-2, 5)) +
  scale_colour_dyson() +
  labs(x = "heliocentric distance (AU, log)",
       y = expression(net~carbon~(mu*mol~m^-2~s^-1)),
       linetype = "k (half-saturation)",
       title = "Q1: whole-organism net carbon vs distance") +
  theme_dyson()
ggsave(file.path(fig_dir, "net_carbon_vs_distance.png"), p1, width = 6, height = 4, dpi = 150)

# Figure 2: crossover distance vs k, with the pre-registered band per class
band <- unique(cross[, c("class", "pred_lo", "pred_hi")])
p2 <- ggplot() +
  geom_rect(data = band, aes(xmin = -Inf, xmax = Inf, ymin = pred_lo, ymax = pred_hi, fill = class), alpha = 0.15) +
  geom_point(data = cross, aes(k, r_star_au, colour = class), size = 2.5) +
  geom_line(data = cross, aes(k, r_star_au, colour = class)) +
  scale_x_log10() +
  scale_colour_dyson() + scale_fill_dyson() +
  labs(x = "k, half-saturation irradiance (log)", y = "crossover distance r* (AU)",
       title = "Q1: crossover distance vs k; band = pre-registered prediction") +
  theme_dyson()
ggsave(file.path(fig_dir, "crossover_vs_k.png"), p2, width = 6, height = 4, dpi = 150)
cat("wrote", fig_dir, "\n")
