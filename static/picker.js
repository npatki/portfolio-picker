$(function(){
    var returns = {};
    var portfolioData;

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
                        symbolLi = $('<li symbol=' + symbol + '>' + symbol + '</li>');
                        symbolB = $('<button type="button">x</button>');
                        symbolB.click(removeSymbol);
                        symbolLi.append(symbolB);
                        $('#companies').append(symbolLi);
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
                $('#results').removeAttr('hidden');
                portfolioData = data;
                table = $('#portfolio');
                keys = Object.keys(returns);
                for(var i=0; i<keys.length; i++){
                    row = $('<tr></tr>');
                    row.append('<td symbol=' + keys[i] + '>' + keys[i] + '</td>');
                    row.append('<td class=num symbol='+ keys[i] + '>0</td>');
                    table.append(row);
                }
                show = parseInt($("#display").attr("value"));
                want = Object.keys(data['fixed_risk']).sort()[5];
                displayReturn(want);
            },
            contentType: "application/json",
            dataType: "json"
        });
    });

    $('#display').change(function(){
        index = parseInt($(this).val());
        want = Object.keys(portfolioData['fixed_risk']).sort()[index];
        displayReturn(want);
    });

    function displayReturn(i){
        data = portfolioData['fixed_risk'][i]['values'];
        num = portfolioData['fixed_risk'][i]['return'];
        for(var symbol in data){
            obj = $('.num[symbol=' + symbol + ']');
            $(obj[0]).html(Number(data[symbol]*100).toFixed(2) + "%");
        }
        $('#metric').html(Number(num*100).toFixed(2) + "%");
    };

    function removeSymbol(){
        symbol = $(this).parent().attr('symbol');
        delete returns[symbol];
        $(this).parent().remove();
    };

});
