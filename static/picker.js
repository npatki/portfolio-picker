$(function(){
    $('#ticker').keypress(function(e){
        if(e.which == 13){
            e.preventDefault();
            $.getJSON($URL_ROOT + "stock", {
                ticker: $("#ticker").val()
            }, function(data){
                // TODO: Save this data some where
                // Maybe also try to get the full company name?
                console.log(data.results);
            });
            $(this).val("");
        }
    });
});
