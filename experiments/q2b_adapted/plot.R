#!/usr/bin/env Rscript
# Two figures from the Q2b CSVs. One graph per figure. Reads CSVs only.
args <- commandArgs(trailingOnly = TRUE)
here <- normalizePath(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE))))
in_dir <- if (length(args) >= 1) args[1] else here
repo <- normalizePath(file.path(here, "..", ".."))
source(file.path(repo, "docs", "analysis", "theme.R"))

sweep <- read.csv(file.path(in_dir, "sweep.csv"), comment.char = "#")
limits <- read.csv(file.path(in_dir, "limits.csv"), comment.char = "#")
stopifnot(nrow(sweep) > 0, nrow(limits) > 0)
sweep$omega <- factor(sweep$omega)
fig_dir <- file.path(in_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE)

p1 <- ggplot(sweep, aes(r_au, net_carbon, colour = class, linetype = omega)) +
  geom_hline(yintercept = 0, colour = "grey40") +
  geom_line() +
  scale_x_log10() +
  coord_cartesian(ylim = c(-2, 10)) +
  scale_colour_dyson() +
  labs(x = "heliocentric distance (AU, log)",
       y = expression(net~carbon~(mu*mol~m^-2~s^-1)),
       linetype = expression(Omega~(K)),
       title = "Q2b: net carbon vs distance, optimum adapted at 1 AU") +
  theme_dyson()
ggsave(file.path(fig_dir, "net_carbon_adapted.png"), p1, width = 8, height = 4.5, dpi = 150)

p2 <- ggplot(limits, aes(omega, outer_au, colour = class)) +
  geom_point(size = 3) + geom_line() +
  scale_colour_dyson() +
  labs(x = expression(Omega~(K)), y = "outer limit (AU)",
       title = "Q2b: sensitivity of the outer limit to the ungrounded Omega") +
  theme_dyson()
ggsave(file.path(fig_dir, "outer_limit_vs_omega.png"), p2, width = 8, height = 4.5, dpi = 150)
cat("wrote", fig_dir, "\n")
