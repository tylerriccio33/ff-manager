
library(jsonlite)
library(ffscrapr)

 # Collect Values #
 n_qb <- 2
  qb_expr <- glue::glue("{n_qb}qb$")
  vals <- ffscrapr::dp_values() %>%
    dplyr::select(player, pos, fp_id, matches(qb_expr))

readr::write_csv(vals, "data/sleeper/draft_values.csv")

