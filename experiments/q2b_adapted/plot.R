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

# 1.1945 AU: the binding thermal floor (classify_limit's "temperature"
# candidate, r_home_au * (T_eq(r_home_au)/t_min)**2), constant across Omega
# because none of its inputs depend on Omega. See RESULTS.md sections 4 and 6:
# this is the limit the run actually found binding, NOT the carbon crossover
# plotted below -- it is drawn on both figures so neither one visually asserts
# the falsified "carbon" prediction on its own.
# Hand-carried constant: limits.csv records outer_au and binding but NOT the
# thermal candidate, so this cannot be derived from the data this script reads
# and cannot be validated against it. If the prereg's r_home_au, area_ratio or
# algal t_min ever change, this WILL silently desync. Value = r_home *
# (T_eq(r_home, ar=4)/t_min)^2 = 1.0 * (278.3112/254.65)^2.
thermal_floor_au <- 1.1945

p1 <- ggplot(sweep, aes(r_au, net_carbon, colour = class, linetype = omega)) +
  geom_hline(yintercept = 0, colour = "grey40") +
  geom_vline(xintercept = thermal_floor_au, colour = "grey30", linetype = "dashed") +
  geom_line() +
  annotate("text", x = thermal_floor_au, y = 5, label = "binding thermal floor",
           angle = 90, vjust = -0.6, hjust = 0, colour = "grey30", size = 3) +
  
  scale_x_log10() +
  coord_cartesian(ylim = c(-2, 10)) +
  scale_colour_dyson() +
  labs(x = "heliocentric distance (AU, log)",
       y = expression(net~carbon~(mu*mol~m^-2~s^-1)),
       linetype = expression(Omega~(K)),
       title = "Q2b: net carbon vs distance, optimum adapted at 1 AU") +
  theme_dyson()
ggsave(file.path(fig_dir, "net_carbon_adapted.png"), p1, width = 8, height = 4.5, dpi = 150)

# y = outer_au = the net-carbon crossover, NOT the outer limit: this run
# determined the outer limit is binding = temperature (flat at
# thermal_floor_au) at every Omega in the grid, so a figure titled "the outer
# limit" would show it doubling when the actual limit does not move. See
# RESULTS.md section 4.
p2 <- ggplot(limits, aes(omega, outer_au, colour = class)) +
  geom_hline(yintercept = thermal_floor_au, colour = "grey30", linetype = "dashed") +
  annotate("text", x = max(limits$omega), y = thermal_floor_au,
           label = "binding thermal floor (1.1945 AU)",
           vjust = -0.6, hjust = 1, colour = "grey30", size = 3) +
  geom_point(size = 3) + geom_line() +
  scale_colour_dyson() +
  labs(x = expression(Omega~(K)), y = "net-carbon crossover (AU)",
       title = "Q2b: sensitivity of the net-carbon crossover to the ungrounded Omega") +
  theme_dyson()
ggsave(file.path(fig_dir, "outer_limit_vs_omega.png"), p2, width = 8, height = 4.5, dpi = 150)
cat("wrote", fig_dir, "\n")
