"""Small live smoke test for the read-only AWS data adapter."""

from aws_data_source import list_games, load_pitch_data


def main() -> None:
    games = list_games(limit=5)
    print("Recent games:")
    print(games.to_string(index=False))

    if games.empty:
        print("\nNo games were returned.")
        return

    game_id = games.iloc[0]["GameID"]
    pitches = load_pitch_data(game_ids=[game_id], limit=5)
    print(f"\nSample pitches for {game_id}:")
    print(pitches.to_string(index=False))


if __name__ == "__main__":
    main()
