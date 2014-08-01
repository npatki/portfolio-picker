$(function(){
    var returns = {};
    var portfolioData;

    $('#ticker').keypress(function(e){

        if(e.which == 13){

            e.preventDefault();
            var symbol = $('#ticker').val();

            $.getJSON(
                $URL_ROOT + 'stock',
                { ticker: symbol},
                function(data){
                    if(data.results === undefined){
                        console.log(data.error);
                    } else {
                        returns[symbol] = data.results;
                        $('#slider').prop('disabled', false);
                        optimizePortfolio();
                    }
            });
            $(this).val("");
        }
    });

    $('#slider').change(function(){
        index = parseInt($(this).val());
        sliderChanged(index);
    });

    // optimize current results
    function optimizePortfolio(){
        if(Object.keys(returns).length == 0){
           return 
        }
        $.ajax({
            type: 'POST',
            url: $URL_ROOT + 'portfolio',
            data: JSON.stringify(returns),
            success: function(data){
                portfolioData = data;
                table = $('#results');
                table.empty();
                keys = Object.keys(returns);
                show = parseInt($('#slider').val());

                ret = portfolioData['fixed_risk'][show]['return'];
                risk = portfolioData['fixed_risk'][show]['risk'];
                $('#return').html(format(ret, false));
                $('#risk').html(format(risk, false));

                showData = portfolioData['fixed_risk'][show]['values'];
                for(var i=0; i<keys.length; i++){
                    name = keys[i];
                    row = $('<tr symbol="' + name + '"></tr>');
                    row.append('<td>' + name + '</td>');
                    if(name in showData){
                        data = $('<td class="data"></td>');
                        data.html(format(showData[name]));
                        row.append(data);
                    } else {
                        row.append('<td class="data">' + format("0") + '</td>');
                    }
                    last_col = $('<td></td>');
                    button = $('<button type="button">x</button>');
                    button.click(removeSymbol);
                    last_col.append(button);
                    row.append(last_col);
                    table.append(row);
                }
            },
            contentType: 'application/json',
            dataType: 'json' 
        });
    }

    // format the percentage
    function format(num, pos){
        round = pos;
        if(pos === undefined){
            round = true;
        }
        val = (parseFloat(num)*100).toFixed(2);
        if(val <= 0 && round){
            val = parseFloat(0.0).toFixed(2);
        }
        if(val >= 100 && round){
            val = parseFloat(100.0).toFixed(2);
        }
        return val + '%';
    }

    // user has moved the slider to position i
    function sliderChanged(i){
       ret = portfolioData['fixed_risk'][i]['return'];
       risk = portfolioData['fixed_risk'][i]['risk'];
       $('#return').html(format(ret, false));
       $('#risk').html(format(risk, false));

       showData = portfolioData['fixed_risk'][i]['values'];
       keys = Object.keys(showData);
       for(var i=0; i<keys.length; i++){
           ticker = keys[i];
           row = $('tr[symbol=' + ticker + ']')[0];
           data = $(row).find('.data')[0];
           $(data).html(format(showData[ticker]));
       }
    }

    // remove symbol after button x has been clicked
    function removeSymbol(){
        symbol = $(this).parent().parent().attr('symbol');
        delete returns[symbol];
        keys = Object.keys(returns);
        if(keys.length === 0){
            $('#slider').prop('disabled', true);
        }
        $(this).parent().parent().remove();
        optimizePortfolio();
    };
});
