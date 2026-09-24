#!/usr/bin/env Rscript
# Figures from the Q4 CSVs (edges.csv, sweep.csv). One graph per figure. Reads CSVs only.
# Colours/shapes come from docs/analysis/theme.R (palette_failure, palette_tolerance, shapes_sigma).
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
save <- function(p, name, w = 9, h = 5) ggsave(file.path(fig_dir, name), p, width = w, height = h, dpi = 150)
edges$tol_status <- ifelse(is.na(edges$within_tol), NA,
                           ifelse(edges$within_tol %in% c(TRUE, "True"), "within", "outside"))

# 1. P1: measured r_close per sigma for every law, against the registered band
p1 <- subset(edges, prediction == "P1")
p1$config <- factor(p1$config, levels = unique(p1$config))
p1$sigma <- factor(p1$sigma_MPa)
fig1 <- ggplot(p1, aes(y = config)) +
  annotate("rect", xmin = 1.19, xmax = 1.27, ymin = -Inf, ymax = Inf, alpha = 0.12, fill = "grey40") +
  annotate("text", x = 1.23, y = Inf, vjust = 1.3, size = 3.2, colour = "grey30",
           label = "registered band [1.19, 1.27] AU") +
  geom_point(aes(x = expected), shape = 1, size = 4.5, colour = "grey45") +
  geom_point(aes(x = measured, shape = sigma), size = 2.3, colour = palette_failure[["FREEZE"]]) +
  geom_text(aes(x = measured, label = sprintf("%.4f", measured)), vjust = -1.1, size = 2.6) +
  scale_shape_sigma() +
  scale_x_continuous(limits = c(1.145, 1.285), breaks = seq(1.15, 1.275, 0.025)) +
  labs(x = expression(r[close]~"(AU), R = 10 km"), y = NULL, shape = expression(sigma~"(MPa)"),
       title = "Q4 P1: where the window closes in r — binding: FREEZE in every row",
       subtitle = "filled = measured (labelled); open ring = prereg expected row") +
  theme_dyson()
save(fig1, "p1_r_close_by_law.png")

# 2. P2: R_window (primary) per config; the other binding line's root muted
p2 <- subset(edges, prediction == "P2")
p2$config <- factor(p2$config, levels = rev(unique(p2$config)))
win <- subset(p2, quantity == "R_window")
oth <- subset(p2, quantity != "R_window")
# a root that IS the edge (f_floor 0.50: OPAQUE binds) is not a later root
oth <- oth[!mapply(function(c, m) any(abs(win$measured[win$config == c] - m) < 1e-9), oth$config, oth$measured), ]
oth$what <- paste0(sub("_root", "", oth$quantity), " root (not the edge)")
bad <- subset(p2, tol_status == "outside")
fig2 <- ggplot() +
  annotate("rect", xmin = 60, xmax = 300, ymin = -Inf, ymax = Inf, alpha = 0.12, fill = "grey40") +
  annotate("text", x = sqrt(60 * 300), y = Inf, vjust = 1.3, size = 3.2, colour = "grey30",
           label = "registered band [60, 300] km (applies to the registered row)") +
  geom_point(data = oth, aes(measured, config), shape = 124, size = 4, colour = "grey60") +
  geom_text(data = oth, aes(measured, config, label = what), vjust = -1.4, size = 2.5, colour = "grey50") +
  geom_point(data = p2, aes(expected, config), shape = 1, size = 4.5, colour = "grey45", na.rm = TRUE) +
  geom_point(data = win, aes(measured, config, colour = binding), size = 3) +
  geom_text(data = win, aes(measured, config, label = sprintf("%.1f km", measured)), vjust = 1.9, size = 2.6) +
  geom_text(data = bad, aes(measured, config, label = "OPAQUE root outside tolerance\n(10.584 vs printed 10.6 km)"),
            hjust = -0.15, vjust = 0.5, size = 2.6, colour = palette_tolerance[["outside"]]) +
  scale_x_log10(limits = c(8, 1200), breaks = c(10, 30, 60, 100, 300, 1000)) +
  scale_colour_failure(name = "R_window binding") +
  labs(x = "R (km, log), r = 1.10 AU, σ 0.7 MPa", y = NULL,
       title = "Q4 P2: R_window per configuration",
       subtitle = "filled = measured R_window; open ring = prereg expected; grey bar = the other line's later root") +
  theme_dyson() + theme(legend.box.margin = margin(0, 20, 0, 20))
save(fig2, "p2_R_window_by_config.png", w = 10, h = 5.5)

# 3. Measured minus expected for every compared row, in units of its edge tolerance
cmp <- subset(edges, !is.na(expected))
cmp$z <- cmp$delta / cmp$tolerance
unit_tol <- ifelse(cmp$unit == "AU", sprintf("tol %g AU", cmp$tolerance), sprintf("tol %.4f km", cmp$tolerance))
cmp$label <- paste0(cmp$config, " · ", cmp$quantity, " · σ", cmp$sigma_MPa, " (", unit_tol, ")")
cmp$label <- factor(cmp$label, levels = rev(unique(cmp$label)))
fig3 <- ggplot(cmp, aes(z, label, colour = tol_status)) +
  geom_vline(xintercept = c(-1, 1), linetype = "dashed", colour = "grey50") +
  geom_point(size = 2) +
  scale_colour_tolerance(name = "against the row's tolerance") +
  labs(x = "(measured - expected) / edge tolerance", y = NULL,
       title = "Q4: every edge row against the prereg's printed value") +
  theme_dyson(base_size = 10)
save(fig3, "rows_vs_expected.png", w = 10, h = 8)

# 4. Registered-grid census: first violated line over (r, R), one panel per sigma
n <- table(factor(sweep$first_violated, levels = names(palette_failure)))
labs_n <- setNames(sprintf("%s (%s nodes)", names(n), formatC(as.integer(n), big.mark = ",", format = "d")), names(n))
sweep <- subset(sweep, first_violated != "STARVE")  # never first-violated; named in the subtitle
sweep$first_violated <- factor(sweep$first_violated, levels = setdiff(names(palette_failure), "STARVE"))
sweep$sigma_lab <- paste0("σ = ", sweep$sigma_MPa, " MPa")
reads <- data.frame(sigma_lab = unique(sweep$sigma_lab))
fig4 <- ggplot(sweep, aes(r_au, R_m / 1e3)) +
  geom_tile(aes(fill = first_violated)) +
  geom_hline(yintercept = 10, linetype = "dashed", colour = "black", linewidth = 0.3) +
  annotate("segment", x = 1.19, xend = 1.27, y = 10, yend = 10, linewidth = 1.6, colour = "black") +
  annotate("text", x = 1.28, y = 10, hjust = 0, vjust = -0.6, size = 2.6, label = "P1 read: R = 10 km,\nband 1.19–1.27 AU") +
  geom_vline(xintercept = 1.10, linetype = "dotted", colour = "black", linewidth = 0.3) +
  annotate("segment", x = 1.10, xend = 1.10, y = 60, yend = 300, linewidth = 1.6, colour = "black") +
  annotate("text", x = 1.115, y = 0.05, hjust = 0, size = 2.6, label = "P2 read: r = 1.10 AU,\nband 60–300 km") +
  facet_wrap(~sigma_lab) +
  scale_y_log10(breaks = c(0.01, 0.1, 1, 10, 100, 1000), labels = c("0.01", "0.1", "1", "10", "100", "1000")) +
  scale_fill_manual(values = palette_failure[names(palette_failure) != "STARVE"], labels = labs_n, name = "first violated") +
  coord_cartesian(xlim = c(1.04, 1.6)) +
  labs(x = "r (AU)", y = "R (km, log)",
       title = "Q4 registered grid: where the vessel lives (auto path, registered law)",
       subtitle = "r shown to 1.6 AU; beyond it every node FREEZEs. Node counts over all three σ; STARVE (0 nodes) is never first-violated.") +
  theme_dyson()
save(fig4, "census_first_violated.png", w = 11, h = 5)
cat("wrote", fig_dir, "\n")
