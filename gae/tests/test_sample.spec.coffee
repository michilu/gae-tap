"use strict"
# Refs. https://github.com/scotch/angular-brunch-seed/blob/master/test/unit
# Rev. 1187280


# jasmine specs for controllers go here

# TODO figure out how to test Controllers that use modules
describe "controllers", ->

  beforeEach(module "app.controllers")

  describe "MyCtrl1", ->

    it "should make scope testable", inject ($rootScope, $controller) ->
      scope = $rootScope.$new()
      ctrl = $controller "MyCtrl1",
        $scope: scope,
      expect(scope.onePlusOne).toEqual(2)

  describe "MyCtrl2", ->

    it "should..."


# jasmine specs for directives go here
describe "directives", ->

  beforeEach(module "app.directives")

  describe "app-version", ->

    it "should print current version", ->
      module ($provide) ->
        $provide.value "version", "TEST_VER"
        return

      inject ($compile, $rootScope) ->
        element = $compile("<span app-version></span>")($rootScope)
        expect(element.text()).toEqual "TEST_VER"


# jasmine specs for filters go here
describe "filter", ->
  beforeEach(module "app.filters")

  describe "interpolate", ->

    beforeEach(module(($provide) ->
      $provide.value "version", "TEST_VER"
      return
    ))

    it "should replace VERSION", inject((interpolateFilter) ->
      expect(interpolateFilter("before %VERSION% after")).toEqual "before TEST_VER after"
    )


# jasmine specs for services go here

describe "service", ->

  beforeEach(module "app.services")

  describe "version", ->
    it "should return current version", inject((version) ->
      expect(version).toEqual "0.1"
    )
