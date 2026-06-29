-module(home_handler).
-behaviour(cowboy_handler).
-export([init/2]).

init(Req, State) ->
    {ok, Rows} = test_app_db:q(
        "SELECT id, name, created_at FROM example ORDER BY id LIMIT 20"
    ),
    Items = [#{id => Id, name => Name, created_at => Ts}
             || [Id, Name, Ts] <- Rows],
    Req2 = test_app_handler:render(Req, "home.html", #{
        title => <<"Welcome">>,
        items => Items
    }),
    {ok, Req2, State}.
