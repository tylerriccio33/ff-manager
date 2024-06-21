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
SEASON <- 2024

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

build_draft_order <- function(con, ..., clean = T) {
  # h2h_winpct then points_for
  # ... is additional tie breakers
  standings <- ffscrapr::ff_standings(con)

  ordered <- standings %>%
    arrange(.data$h2h_winpct, .data$points_for, ...)

  if (clean) {
    ordered <- ordered %>%
      select(franchise_id, franchise_name) %>%
      mutate(order = row_number())
  }

  return(ordered)
}

build_draft_template <- function(rounds, picks) {
  ### build a lookup of raw pick to round, pick ###

  pick_vec <- seq_len(picks)
  round_vec <- seq_len(rounds)
  expanded_draft <- tidyr::expand_grid(round = 1:rounds, pick = 1:picks)
  draft_with_raw_order <- expanded_draft %>%
    mutate(raw_pick = row_number())

  return(draft_with_raw_order)
}

derive_raw_pick_from_vals <- function(vals, rm_og_pick_col = T) {
  # the values are formatted as 2023 Pick 1.01
  # this must be converted into a raw pick
  vals <- vals %>%
    mutate(picks = str_sub(pick, start = -4)) %>%
    arrange(picks) %>%
    mutate(raw_pick = row_number())
  cli::cli_inform("Draft Pick/Value Tibble")
  print(vals)
  if (rm_og_pick_col) {
    vals <- select(vals, -pick)
  } else {
    cli_alert_danger("The value pick column ('2023 Pick 1.01') wasn't removed. You probably meant to remove this.")
  }
}


Draft <- function(lg, .season, vals) {
  cli::cli_h2("Initiating Draft Pull")

  # Get Current Assets:
  # - gets franchise, round and original owner
  present_pick_assets <- ffscrapr::ff_draftpicks(lg) %>%
    dplyr::filter(.data$season == .season + 1) %>%
    dplyr::select(franchise_id, franchise_name, original_franchise_id, round)
  cli::cli_inform("Present Pick Assets: ")
  print(present_pick_assets)


  ### Append Picks to Rounds ###
  # - rebuild the draft w/no trades
  # - derive raw picks; link round, pick and original owner to raw
  # - execute all trades

  # Build Original Draft:
  original_draft_order <- build_draft_order(lg, clean = T)
  cli::cli_inform("Original Draft Order: ")
  print(original_draft_order)
  max_rounds <- max(present_pick_assets$round)
  n_teams <- dplyr::n_distinct(present_pick_assets$franchise_id)
  draft_template <-
    build_draft_template(rounds = max_rounds, picks = n_teams)
  full_original_draft <- left_join(
    x = draft_template,
    y = original_draft_order,
    by = c("pick" = "order")
  )
  cli::cli_inform("Full Original Draft: ")
  print(full_original_draft)

  # Switch Owners of Original Order:
  aquired_picks <- filter(present_pick_assets, franchise_id != original_franchise_id)

  


  # Join Pick to Current Assets #
  # use the round + original_franchise_id to get the raw pick
  original_draft_lookup <- select(full_original_draft,
    round, pick, raw_pick,
    original_franchise_id = franchise_id
  )


  # we have the current round and original franchise owner
  # - this is the present_pick_assets

  # we have the

  left_join(
    x = present_pick_assets,
    y = original_draft_lookup,
    by = c("round", "original_franchise_id")
  )

  present_pick_assets <- left_join(
    x = present_pick_assets,
    y = select(full_original_draft, round, pick, raw_pick, original_franchise_id = franchise_id),
    by = c("round", "original_franchise_id")
  )



  foo <- arrange(present_pick_assets, raw_pick)
  print(foo)

  # Get Draft Values #
  season_expr <- glue::glue("^{.season} Pick")
  draft_vals <- vals %>%
    dplyr::filter(stringr::str_detect(.data$player, season_expr)) %>%
    dplyr::rename(pick = player) %>%
    dplyr::select(-fp_id) %>%
    derive_raw_pick_from_vals(rm_og_pick_col = T)

  # Join Value to Round-Pick #
  present_pick_assets <- left_join(
    x = present_pick_assets,
    y = draft_vals,
    by = "raw_pick"
  ) %>%
    select(-c(pos))


  # Return Class #
  cls <-
    list(
      "original_order" = original_draft_order,
      "vals" = draft_vals,
      "present_pick_assets" = present_pick_assets
    )


  return(cls)
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



  # Collect Draft Picks #
  draft <- Draft(
    lg = lg,
    .season = season,
    vals = vals
  )
  draft_assets <- draft$present_pick_assets
  cli::cli_inform("Draft Assets: ")
  print(draft_assets)

  nested_picks <- draft_assets %>%
    dplyr::group_by(franchise_name) %>%
    tidyr::nest(.key = "picks")

  # Join Picks and Rosters #
  all_assets <- dplyr::left_join(
    x = nested_rosters,
    y = nested_picks,
    by = "franchise_name"
  ) %>%
    dplyr::ungroup() %>%
    dplyr::mutate(all_assets = purrr::map2(roster, picks, \(x, y) vctrs::vec_rbind(x, y)))

  # Get Non-Rostered #
  non_rostered <- dplyr::anti_join(
    x = ids,
    y = rosters,
    by = c("id" = "player_id")
  ) %>%
    tidyr::drop_na() %>%
    dplyr::inner_join(
      y = vals,
      by = "fp_id"
    ) %>%
    dplyr::select(-fp_id)


  # Set up Class #
  cls <- list(
    "lg" = lg,
    "non_rostered" = non_rostered,
    "all_rostered_assets" = all_assets
  )

  # Unnest Assets Method #
  unnest_roster_element <- function(self, elem) {
    valid_elems <- c("roster", "pick", "all_assets")
    string_elem <- rlang::enexpr(elem) %>% as.character()
    if (!string_elem %in% valid_elems) {
      cli::cli_abort(c(
        "Elem {.var string_elem} must be in {valid_elems}"
      ))
    }
    dt <- self$all_rostered_assets[[1]]
    unnested <- dplyr::select(dt, franchise_name, {{ elem }}) %>%
      tidyr::unnest()
    return(unnested)
  }
  cls[["unnest_roster_element"]] <- unnest_roster_element

  return(cls)
}

foo <- FFData()

data <- foo$all_rostered_assets %>%
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
