"use strict"

angular.module("app", [
  "app.controllers"
])

angular.module("app.controllers", [])

.controller("Ctrl", [
  "$scope"
  "$log"

($scope, $log) ->

  $scope.$watch "host", (newValue, oldValue) ->
    if newValue is ""
      if $scope.DEBUG
        $scope.application_url = ""
      else
        $scope.application_url = "http://#{$scope.app_id}.appspot.com"
    else
      $scope.application_url = "//#{newValue}"
    unless $scope.$$phase
      $scope.$apply()
    return

  return
])

angular.element(document).ready ->
  angular.bootstrap(document, ["app"])
