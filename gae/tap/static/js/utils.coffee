"use strict"

angular.module("utils", [
])


.directive("formBackground",
->
  ($scope, elm, attrs) ->
    $form = $(elm)
    $form.submit (e) ->
      $.ajax
        type: $form.attr("method")
        url: $form.attr("action")
        data: $form.serializeArray()
      .done (_data, _textStatus, _jqXHR) ->
        return
      .fail (_jqXHR, textStatus, _errorThrown) ->
        if textStatus and not PRODUCTION?
          console.log textStatus
        return
      return false
)

.directive("feedbackFormBackground",
->
  ($scope, elm, attrs) ->
    $form = $(elm)
    $form.submit (e) ->
      $("[name|=entry\\.2\\.single]", $form).val(window.location.href)
      $.ajax
        type: $form.attr("method")
        url: $form.attr("action")
        data: $form.serializeArray()
      .done (response) ->
        error = $(".errorheader", response).text()
        message = $(".ss-custom-resp", response).text()
        if error and not PRODUCTION?
          console.log error
        $form.closest(".modal").modal("hide")
        $scope.$apply ->
          $scope.description = ""
          return
        return
      return false
)
