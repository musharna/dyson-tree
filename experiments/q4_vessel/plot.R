#!/usr/bin/env Rscript
# Figures from the Q4 CSVs (edges.csv, sweep.csv). One graph per figure. Reads CSVs only.
args <- commandArgs(trailingOnly = TRUE)
here <- normalizePath(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE))))
in_dir <- if (length(args) >= 1) args[1] else here
repo <- normalizePath(file.path(here, "..", ".."))
source(file.path(repo, "docs", "analysis", "theme.R"))

edges <- read.csv(file.path(in_dir, "edges.csv"), comment.char = "#", stringsAsFactors = FALSE)
sweep <- read.csv(file.path(in_dir, "sweep.csv"), comment.char = "#", stringsAsFactors = FALSE)
stopifnot(nrow(edges) > 0, nrow(sweep) > 0)
fig_dir <- file.path(in_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE)
save <- function(p, name, w = 8, h = 4.5) ggsave(file.path(fig_dir, name), p, width = w, height = h, dpi = 150)

# 1. P1: measured r_close per sigma for every law, against the registered band
p1 <- subset(edges, prediction == "P1")
p1$config <- factor(p1$config, levels = unique(p1$config))
p1$sigma <- factor(p1$sigma_MPa)
fig1 <- ggplot(p1, aes(measured, config, colour = sigma)) +
  annotate("rect", xmin = 1.19, xmax = 1.27, ymin = -Inf, ymax = Inf, alpha = 0.12, fill = "grey40") +
  geom_point(aes(x = expected), shape = 4, size = 3, colour = "grey30") +
  geom_point(size = 2.5) +
  labs(x = expression(r[close]~"(AU), R = 10 km"), y = NULL, colour = expression(sigma~"(MPa)"),
       title = "Q4 P1: window closes in r; grey band = registered [1.19, 1.27] AU",
       subtitle = "dots measured; x = prereg expected row") +
  theme_dyson()
save(fig1, "p1_r_close_by_law.png")

# 2. P2: R_window and the other line's root for every config, against the band
p2 <- subset(edges, prediction == "P2")
p2$config <- factor(p2$config, levels = rev(unique(p2$config)))
fig2 <- ggplot(p2, aes(measured, config, shape = quantity, colour = binding)) +
  annotate("rect", xmin = 60, xmax = 300, ymin = -Inf, ymax = Inf, alpha = 0.12, fill = "grey40") +
  geom_point(aes(x = expected), shape = 4, size = 3, colour = "grey30", na.rm = TRUE) +
  geom_point(size = 2.5) +
  scale_x_log10() +
  scale_colour_manual(values = c(OPAQUE = "#1565C0", FREEZE = "#C62828")) +
  labs(x = "R (km, log), r = 1.10 AU, σ 0.7 MPa", y = NULL, colour = "binding at the edge",
       shape = NULL, title = "Q4 P2: window closes in R; grey band = registered [60, 300] km",
       subtitle = "dots measured; x = prereg expected row") +
  theme_dyson()
save(fig2, "p2_R_window_by_config.png")

# 3. Measured minus expected for every compared row, in units of the edge tolerance
cmp <- subset(edges, !is.na(expected))
cmp$within_tol <- as.character(cmp$within_tol)
cmp$z <- cmp$delta / cmp$tolerance
cmp$label <- paste(cmp$row, cmp$quantity, paste0("σ", cmp$sigma_MPa))
cmp$label <- factor(cmp$label, levels = rev(cmp$label))
fig3 <- ggplot(cmp, aes(z, label, colour = within_tol)) +
  geom_vline(xintercept = c(-1, 1), linetype = "dashed", colour = "grey50") +
  geom_point(size = 2) +
  scale_colour_manual(values = c(True = "#2E7D32", False = "#C62828")) +
  labs(x = "(measured - expected) / edge tolerance", y = NULL, colour = "within tolerance",
       title = "Q4: every edge row against the prereg's printed value") +
  theme_dyson(base_size = 10)
save(fig3, "rows_vs_expected.png", h = 8)

# 4. Census of the registered grid: first violated line over (r, R), one panel per sigma
sweep$first_violated <- factor(sweep$first_violated, levels = c("HELD", "FREEZE", "STARVE", "OPAQUE"))
fig4 <- ggplot(sweep, aes(r_au, R_m / 1e3, fill = first_violated)) +
  geom_tile() +
  facet_wrap(~sigma_MPa, labeller = label_both) +
  scale_y_log10() +
  scale_fill_manual(values = c(HELD = "#2E7D32", FREEZE = "#90CAF9", STARVE = "#8D6E63", OPAQUE = "#424242"),
                    drop = FALSE) +
  coord_cartesian(xlim = c(1.04, 1.6)) +
  labs(x = "r (AU)", y = "R (km, log)", fill = "first violated",
       title = "Q4 registered grid: where the vessel lives (auto path, registered law)",
       subtitle = "r shown to 1.6 AU; beyond it every node FREEZEs") +
  theme_dyson()
save(fig4, "census_first_violated.png", w = 10, h = 4.5)

# 5. Census counts per sigma
cen <- as.data.frame(table(sigma = sweep$sigma_MPa, first = sweep$first_violated))
cen <- subset(cen, Freq > 0)  # STARVE is never first-violated; a zero bar has no log height
fig5 <- ggplot(cen, aes(factor(sigma), Freq, fill = first)) +
  geom_col(position = "dodge") +
  scale_y_log10() +
  scale_fill_manual(values = c(HELD = "#2E7D32", FREEZE = "#90CAF9", STARVE = "#8D6E63", OPAQUE = "#424242")) +
  labs(x = "σ (MPa)", y = "grid nodes (log)", fill = "first violated",
       title = "Q4 registered grid census: 197 x 101 nodes per σ") +
  theme_dyson()
save(fig5, "census_counts.png")
cat("wrote", fig_dir, "\n")
