library(ffscrapr)
library(ffpros)
library(tibble)
library(stringr)
library(dplyr)
library(ffopportunity)
library(jsonlite)
library(glue)

options(pillar.print_max = Inf)

# TODO: format

LEAGUE_ID <- "1049399476387028992"
SEASON <- 2025

ssb <- ff_connect(
  platform = "sleeper",
  league_id = LEAGUE_ID, 
  season = SEASON
)

get_player_data <- function(ssb) {
  # Rosters:
  rosters <- ff_rosters(ssb) %>%
    select(
      team = franchise_name,
      id = player_id,
      name = player_name,
      pos
    )

  # Arrange Values:
  player_ids <- dp_playerids() %>%
    select(id = sleeper_id, fp_id = fantasypros_id)
  player_values <- dp_values("values-players.csv") %>%
    left_join(player_ids, by = "fp_id") %>%
    select(id,
      dynasty_value = value_1qb,
      fp_id
    ) %>%
    left_join(y = {
      fp_rankings(page = "consensus-cheatsheets") %>%
        select(
          fp_id = fantasypros_id,
          starter_value = player_owned_espn
        )
    })

  # Link Back:
  player_data <- left_join(rosters, player_values)

  return(player_data)
}


FFData <- function(platform = "sleeper",
                   league_id = "985411219362246656",
                   season = 2025,
                   n_qb = 2,
                   draft_order_agnostic = T) {
  # Connect League #
  lg <- ffscrapr::ff_connect(
    platform = platform,
    league_id = league_id,
    season = season
  )

  # Collect Rosters #
  rosters <- ffscrapr::ff_rosters(lg) %>%
    select(-c(team, age, franchise_id))
        print("Joined Rosters:")
    print(rosters)

  # Collect Values #
  qb_expr <- glue::glue("{n_qb}qb$")
  vals <- ffscrapr::dp_values() %>%
    select(player, pos, fp_id, matches(qb_expr))

  # Collect IDs #
  id_col <- dplyr::case_match(platform,
    "sleeper" ~ "sleeper_id",
    .default = rlang::na_chr
  )
  ids <- ffscrapr::dp_playerids() %>%
    select(id = {{ id_col }}, fp_id = fantasypros_id)

  # Join #
  joined_rosters <- dplyr::left_join(
    x = rosters,
    y = ids,
    by = c("player_id" = "id")
  ) %>%
    left_join(
      y = select(vals, -c(player, pos)),
      by = "fp_id"
    )
    print("Joined Rosters:")
    print(joined_rosters)

  # Nest Players into Team #
  nested_rosters <- dplyr::group_by(joined_rosters, franchise_name) %>%
    tidyr::nest(.key = "roster")

return(nested_rosters)
}

nested_rosters <- FFData()

data <- nested_rosters %>%
  select(team = franchise_name, assets = all_assets) %>%
  tidyr::unnest(assets) %>%
  select(team,
    id = player_id, name = player_name, pos, fp_id, dynasty_value = value_2qb,
    pick_number = raw_pick
  ) %>%
  left_join(y = {
    fp_rankings(page = "consensus-cheatsheets") %>%
      select(
        fp_id = fantasypros_id,
        starter_value = player_owned_espn
      )
  })

json_data <- toJSON(data)

write(json_data, "data/sleeper_assets.json")
cli::cli_alert_success("yay yay yay ~~~~!!!!!")
