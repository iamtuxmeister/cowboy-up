-module(test_app_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one, intensity => 10, period => 60},
    Children = prod_children() ++ dev_children(),
    {ok, {SupFlags, Children}}.

prod_children() ->
    [
        %% Add your workers here:
        %% #{id => my_worker, start => {my_worker, start_link, []}, type => worker}
    ].

dev_children() ->
    case application:load(fs) of
        ok                           -> application:ensure_all_started(fs), watcher_child();
        {error, {already_loaded, fs}} -> watcher_child();
        {error, _}                   -> []
    end.

watcher_child() ->
    [#{id      => test_app_watcher,
       start   => {test_app_watcher, start_link, []},
       restart => permanent,
       type    => worker}].
