"use strict"
# Refs. https://github.com/scotch/angular-brunch-seed/tree/master/app
# Rev. 1187280


# Declare app level module which depends on filters, and services
angular.module("app", [
  "ngCookies"
  "ngResource"
  "app.controllers"
  "app.directives"
  "app.filters"
  "app.services"
  "utils"
])

.config([
  "$routeProvider"
  "$locationProvider"
  "$interpolateProvider"

($routeProvider, $locationProvider, $interpolateProvider, config) ->

  $routeProvider

    .when("/todo", {templateUrl: "/partials/todo.html"})
    .when("/view1", {templateUrl: "/partials/partial1.html"})
    .when("/view2", {templateUrl: "/partials/partial2.html"})

    # Catch all
    .otherwise({redirectTo: "/todo"})

  # Without server side support html5 must be disabled.
  $locationProvider.html5Mode(false)

  $interpolateProvider.startSymbol "[["
  $interpolateProvider.endSymbol "]]"

  return
])


### Controllers ###

angular.module("app.controllers", [])

.controller("AppCtrl", [
  "$scope"
  "$location"
  "$log"

($scope, $location, $log) ->
  unless $scope.$$phase?
    $scope.$apply()

  # Uses the url to determine if the selected
  # menu item should have the class active.
  $scope.$location = $location
  $scope.$watch("$location.path()", (path) ->
    $scope.activeNavId = path || "/"
  )

  # getClass compares the current url with the id.
  # If the current url starts with the id it returns "active"
  # otherwise it will return "" an empty string. E.g.
  #
  #   # current url = "/products/1"
  #   getClass("/products") # returns "active"
  #   getClass("/orders") # returns ""
  #
  $scope.getClass = (id) ->
    if $scope.activeNavId.substring(0, id.length) == id
      return "active"
    else
      return ""
])

.controller("MyCtrl1", [
  "$scope"

($scope) ->
  $scope.onePlusOne = 2
])

.controller("MyCtrl2", [
  "$scope"

($scope) ->
  $scope
])

.controller("TodoCtrl", [
  "$scope"

($scope) ->

  $scope.todos = [
    text: "learn angular"
    done: true
  ,
    text: "build an angular app"
    done: false
  ]

  $scope.addTodo = ->
    $scope.todos.push
      text: $scope.todoText
      done: false

    $scope.todoText = ""

  $scope.remaining = ->
    count = 0
    angular.forEach $scope.todos, (todo) ->
      count += (if todo.done then 0 else 1)

    count

  $scope.archive = ->
    oldTodos = $scope.todos
    $scope.todos = []
    angular.forEach oldTodos, (todo) ->
      $scope.todos.push todo  unless todo.done

])


### Directives ###

# register the module with Angular
angular.module("app.directives", [
  # require the "app.service" module
  "app.services"
])

.directive("appVersion", [
  "version"

(version) ->

  (scope, elm, attrs) ->
    elm.text(version)
])

.directive("i18n",
->
  ($scope, elm, _attrs) ->
    elm.text gettext("Dumeril")
)


### Filters ###

angular.module("app.filters", [])

.filter("interpolate", [
  "version",

(version) ->
  (text) ->
    String(text).replace(/\%VERSION\%/mg, version)
])


### Sevices ###

angular.module("app.services", [])

.factory "version", -> "0.1"


### Init ###

angular.element(document).ready ->
  angular.bootstrap(document, ["app"])
