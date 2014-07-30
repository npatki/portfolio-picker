$(function(){
    var returns = {};

    $('#ticker').keypress(function(e){

        if(e.which == 13){

            e.preventDefault();
            var symbol = $('#ticker').val();

            $.getJSON($URL_ROOT + 'stock',
                {
                    ticker: symbol
                },
                function(data){
                    if(data.results === undefined){
                        console.log(data.error);
                    } else {
                        returns[symbol] = data.results;
                        $('#companies').append('<li>' + symbol + '</li>');
                    }
            });
            $(this).val("");
        }
    });

    $('#submit').click(function(){
        $.ajax({
            type: "POST",
            url: $URL_ROOT + "portfolio",
            data: JSON.stringify(returns),
            success: function(data){
                console.log(data);
            },
            contentType: "application/json",
            dataType: "json"
        });
    });
});
